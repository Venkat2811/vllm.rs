#!/usr/bin/env bash
# Reproduce the TensorPuffer Direction-B / M0 or M1 FULL_SKIP toy row on an RTX host.
#
# This is intentionally a forced-runner RTX reproduction, not CPU-only:
# the current CLI parses --cpu, but that flag is not wired into device
# selection in this branch.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TPUF_MODE="${TPUF_MODE:-M0}"
TPUF_MODE="${TPUF_MODE^^}"
if [[ "${TPUF_MODE}" != "M0" && "${TPUF_MODE}" != "M1" ]]; then
  echo "error: TPUF_MODE must be M0 or M1, got ${TPUF_MODE}" >&2
  exit 1
fi
RUN_ID="${RUN_ID:-rtx-vllmrs-b-${TPUF_MODE,,}-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_DIR="${OUT_DIR:-/tmp/${RUN_ID}}"
N="${N:-8}"
SEED="${SEED:-123}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-2304}"
MAX_TOKENS="${MAX_TOKENS:-16}"
PREFIX_CACHE_MAX_TOKENS="${PREFIX_CACHE_MAX_TOKENS:-4096}"

VLLM_BIN="${VLLM_BIN:-${ROOT}/target/release/vllm-rs}"
MODEL="${MODEL:-${HOME}/.cache/huggingface/hub/models--bartowski--Llama-3.2-3B-Instruct-GGUF/snapshots/5ab33fa94d1d04e903623ae72c95d1696f09f9e8/Llama-3.2-3B-Instruct-Q4_K_M.gguf}"
TENSORPUFFER_ROOT="${TENSORPUFFER_ROOT:-${ROOT}/../../../../tensorpuffer}"
TPUF_DAEMON_BIN="${TPUF_DAEMON_BIN:-${TENSORPUFFER_ROOT}/target/release/tp-puffer-shm-daemon}"

export TPUF_S3_ENDPOINT="${TPUF_S3_ENDPOINT:-http://127.0.0.1:9100}"
export TPUF_BUCKET="${TPUF_BUCKET:-tensorpuffer}"
export TPUF_S3_BUCKET="${TPUF_S3_BUCKET:-${TPUF_BUCKET}}"
export TPUF_S3_ACCESS_KEY="${TPUF_S3_ACCESS_KEY:-minioadmin}"
export TPUF_S3_SECRET_KEY="${TPUF_S3_SECRET_KEY:-minioadmin}"
export TPUF_S3_REGION="${TPUF_S3_REGION:-us-east-1}"
export TPUF_KVBM_ENABLE=1
export TPUF_KVBM_NAMESPACE="${TPUF_KVBM_NAMESPACE:-${RUN_ID}}"
export TPUF_KVBM_S3_PREFIX="${TPUF_KVBM_S3_PREFIX:-kv/vllm-rs/${RUN_ID}}"
export TPUF_FOYER_RAM_BYTES="${TPUF_FOYER_RAM_BYTES:-536870912}"
export TPUF_FOYER_SSD_BYTES="${TPUF_FOYER_SSD_BYTES:-2147483648}"
export TPUF_FOYER_BLOCK_SIZE_BYTES="${TPUF_FOYER_BLOCK_SIZE_BYTES:-1048576}"
export TPUF_COMPRESS="${TPUF_COMPRESS:-zstd}"
export MYELON_INSTRUMENT="${MYELON_INSTRUMENT:-1}"
export RUST_BACKTRACE="${RUST_BACKTRACE:-1}"

DAEMON_PID=""
cleanup() {
  if [[ -n "${DAEMON_PID}" ]]; then
    kill "${DAEMON_PID}" >/dev/null 2>&1 || true
    wait "${DAEMON_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ ! -x "${VLLM_BIN}" ]]; then
  echo "error: vllm-rs binary not found or not executable: ${VLLM_BIN}" >&2
  echo "build with: cargo build --release --features tensorpuffer" >&2
  exit 1
fi

if [[ ! -f "${MODEL}" ]]; then
  echo "error: model file not found: ${MODEL}" >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if ! curl -fsS "${TPUF_S3_ENDPOINT}/minio/health/live" >/dev/null 2>&1; then
    echo "warning: MinIO health endpoint did not respond at ${TPUF_S3_ENDPOINT}" >&2
  fi
fi

mkdir -p "${OUT_DIR}/prompts" "${OUT_DIR}/cold" "${OUT_DIR}/warm"

if [[ "${TPUF_MODE}" == "M1" ]]; then
  if [[ ! -x "${TPUF_DAEMON_BIN}" ]]; then
    echo "error: tp-puffer-shm-daemon not found or not executable: ${TPUF_DAEMON_BIN}" >&2
    echo "build with: cargo build -p tp-puffer-shm --release --bin tp-puffer-shm-daemon" >&2
    exit 1
  fi
  TPUF_REMOTE_BASE="${TPUF_KVBM_REMOTE_PREFIX:-${RUN_ID}}"
  unset TPUF_KVBM_REMOTE_PREFIX_EXACT
  daemon_args=()
  for phase in cold warm; do
    for i in $(seq 1 "${N}"); do
      daemon_args+=(--prefix "${TPUF_REMOTE_BASE}-${phase}-${i}-engine")
      daemon_args+=(--prefix "${TPUF_REMOTE_BASE}-${phase}-${i}-runner")
    done
  done
  echo "[m1] starting daemon for ${#daemon_args[@]} prefix args under base ${TPUF_REMOTE_BASE}" >&2
  env \
    TPUF_FOYER_SSD_DIR="${OUT_DIR}/daemon-foyer" \
    "${TPUF_DAEMON_BIN}" \
      "${daemon_args[@]}" \
      >"${OUT_DIR}/daemon.log" 2>&1 &
  DAEMON_PID="$!"
  sleep 1
  if ! kill -0 "${DAEMON_PID}" >/dev/null 2>&1; then
    echo "error: tp-puffer-shm-daemon exited early; see ${OUT_DIR}/daemon.log" >&2
    exit 1
  fi
else
  unset TPUF_KVBM_REMOTE_PREFIX
  unset TPUF_KVBM_REMOTE_PREFIX_EXACT
  unset TPUF_KVBM_REMOTE_ROLE
fi

python3 - "${OUT_DIR}/prompts" "${N}" <<'PY'
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
n = int(sys.argv[2])
unit = (
    "You are a careful technical writer. Always cite sources. Keep paragraphs short. "
    "Use plain English. Be precise. Avoid filler. Stay neutral. Cite numbers in SI units. "
    "Do not speculate. End sentences with periods. "
)
questions = [
    "tell me a one-sentence story about Sir Tensor guarding a bridge while counting three falling stars.",
    "explain why a cache hit can skip prefill but still decode one token.",
    "summarize object storage native KV caching in one precise paragraph.",
    "write a neutral status update about a benchmark harness becoming reproducible.",
    "describe a tiny walrus engineer measuring latency with a brass stopwatch.",
    "state why labels must distinguish RTX, CPU, and Mac runs.",
    "explain why a MinIO retry should be documented instead of hidden.",
    "write one sentence about durable artifacts replacing temporary logs.",
]
for i in range(n):
    prompt = unit * 17 + "Now answer: " + questions[i % len(questions)]
    (out / f"p{i + 1}.txt").write_text(prompt, encoding="utf-8")
PY

run_one() {
  local phase="$1"
  local i="$2"
  local restore="$3"
  local try_load="$4"
  local full_skip="$5"
  local prompt_file="${OUT_DIR}/prompts/p${i}.txt"
  local log_file="${OUT_DIR}/${phase}/p${i}.log"

  echo "[${phase}] p${i} -> ${log_file}" >&2
  local run_env=(
    TPUF_FOYER_SSD_DIR="${OUT_DIR}/foyer-${phase}-${i}"
    TPUF_KVBM_RESTORE_ON_START="${restore}"
    TPUF_KVBM_TRY_LOAD="${try_load}"
    TPUF_KVBM_FULL_SKIP="${full_skip}"
  )
  if [[ "${TPUF_MODE}" == "M1" ]]; then
    run_env+=(TPUF_KVBM_REMOTE_PREFIX="${TPUF_REMOTE_BASE}-${phase}-${i}")
  fi
  env \
    "${run_env[@]}" \
    "${VLLM_BIN}" \
      --f "${MODEL}" \
      --max-model-len "${MAX_MODEL_LEN}" \
      --max-num-seqs 1 \
      --max-tokens "${MAX_TOKENS}" \
      --prompts "$(cat "${prompt_file}")" \
      --seed "${SEED}" \
      --force-runner \
      --prefix-cache \
      --prefix-cache-max-tokens "${PREFIX_CACHE_MAX_TOKENS}" \
      >"${log_file}" 2>&1
}

for i in $(seq 1 "${N}"); do
  run_one cold "${i}" 0 0 0
done

for i in $(seq 1 "${N}"); do
  run_one warm "${i}" 1 1 1
done

python3 - "${OUT_DIR}" "${N}" "${TPUF_MODE}" <<'PY'
import json
import math
import pathlib
import re
import sys

out = pathlib.Path(sys.argv[1])
n = int(sys.argv[2])
mode = sys.argv[3]

first_token_re = re.compile(
    r"FirstTokenPath:.*?prefill_roundtrip_ms=(\d+).*?ingress_to_emit_ms=(\d+)"
)
prompt_tokens_re = re.compile(r"Prompt tokens:\s+(\d+)")

def nearest_rank(values, pct):
    values = sorted(values)
    if not values:
        return None
    idx = max(0, min(len(values) - 1, math.ceil((pct / 100.0) * len(values)) - 1))
    return values[idx]

def parse_log(path):
    text = path.read_text(errors="replace")
    ft = first_token_re.search(text)
    toks = prompt_tokens_re.search(text)
    return {
        "path": str(path),
        "tokens": int(toks.group(1)) if toks else None,
        "prefill_rt_ms": int(ft.group(1)) if ft else None,
        "ingress_ms": int(ft.group(2)) if ft else None,
        "full_skip": "[full-skip]" in text,
        "try_load": "[try-load/full-skip]" in text or '"op":"try_full_skip_prefill"' in text,
        "stash": '"op":"stash_kv_local"' in text and '"stashed":true' in text,
        "kvbm_failed": "KVBM init failed" in text,
        "remote": "KVBM using remote daemon" in text,
    }

rows = []
for i in range(1, n + 1):
    cold = parse_log(out / "cold" / f"p{i}.log")
    warm = parse_log(out / "warm" / f"p{i}.log")
    row = {
        "i": i,
        "tokens": warm["tokens"] or cold["tokens"],
        "cold_ingress_ms": cold["ingress_ms"],
        "warm_ingress_ms": warm["ingress_ms"],
        "cold_prefill_rt_ms": cold["prefill_rt_ms"],
        "warm_prefill_rt_ms": warm["prefill_rt_ms"],
        "full_skip": warm["full_skip"],
        "try_load": warm["try_load"],
        "stash": cold["stash"],
        "kvbm_failed": cold["kvbm_failed"] or warm["kvbm_failed"],
        "remote": cold["remote"] or warm["remote"],
    }
    if row["cold_ingress_ms"] and row["warm_ingress_ms"]:
        row["x_ingress"] = row["cold_ingress_ms"] / row["warm_ingress_ms"]
    else:
        row["x_ingress"] = None
    if row["cold_prefill_rt_ms"] and row["warm_prefill_rt_ms"]:
        row["x_prefill_rt"] = row["cold_prefill_rt_ms"] / row["warm_prefill_rt_ms"]
    else:
        row["x_prefill_rt"] = None
    rows.append(row)

cold_ingress = [r["cold_ingress_ms"] for r in rows if r["cold_ingress_ms"] is not None]
warm_ingress = [r["warm_ingress_ms"] for r in rows if r["warm_ingress_ms"] is not None]
cold_rt = [r["cold_prefill_rt_ms"] for r in rows if r["cold_prefill_rt_ms"] is not None]
warm_rt = [r["warm_prefill_rt_ms"] for r in rows if r["warm_prefill_rt_ms"] is not None]
tokens = [r["tokens"] for r in rows if r["tokens"] is not None]

summary = {
    "run_id": out.name,
    "run_dir": str(out),
    "engine": "vllm.rs",
    "direction": "B",
    "mode": f"{mode} RTX forced-runner FULL_SKIP",
    "n": n,
    "tokens_min": min(tokens) if tokens else None,
    "tokens_p50": nearest_rank(tokens, 50),
    "tokens_max": max(tokens) if tokens else None,
    "cold_ingress_ms_p50": nearest_rank(cold_ingress, 50),
    "cold_ingress_ms_p95": nearest_rank(cold_ingress, 95),
    "warm_ingress_ms_p50": nearest_rank(warm_ingress, 50),
    "warm_ingress_ms_p95": nearest_rank(warm_ingress, 95),
    "x_ingress_p50": (
        nearest_rank(cold_ingress, 50) / nearest_rank(warm_ingress, 50)
        if cold_ingress and warm_ingress and nearest_rank(warm_ingress, 50)
        else None
    ),
    "cold_prefill_rt_ms_p50": nearest_rank(cold_rt, 50),
    "warm_prefill_rt_ms_p50": nearest_rank(warm_rt, 50),
    "x_prefill_rt_p50": (
        nearest_rank(cold_rt, 50) / nearest_rank(warm_rt, 50)
        if cold_rt and warm_rt and nearest_rank(warm_rt, 50)
        else None
    ),
    "all_full_skip": all(r["full_skip"] for r in rows),
    "all_try_load": all(r["try_load"] for r in rows),
    "all_stash": all(r["stash"] for r in rows),
    "any_kvbm_failed": any(r["kvbm_failed"] for r in rows),
    "any_remote": any(r["remote"] for r in rows),
    "rows": rows,
}

(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

print(json.dumps(summary, indent=2))
PY

echo "summary: ${OUT_DIR}/summary.json" >&2
