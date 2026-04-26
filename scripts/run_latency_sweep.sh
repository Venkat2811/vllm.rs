#!/usr/bin/env bash
# Latency sweep: 1K-token concurrency × RPS, socket vs myelon (owned, typed)
# Output: per-cell JSON with TTFT/latency p50/p95/p99 + summary curve.

set -u

ARTIFACT_ROOT="${ARTIFACT_ROOT:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-26_phase2_latency_sweep}"
BIN="${BIN:-/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs}"
DATASET="${DATASET:-/root/.cache/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json}"
TOKENIZER="${TOKENIZER:-Qwen/Qwen3-0.6B}"
SERVED_MODEL="${SERVED_MODEL:-Qwen/Qwen3-0.6B}"
PORT="${PORT:-8000}"
DURATION_SEC="${DURATION_SEC:-20}"
WARMUP_RUNS="${WARMUP_RUNS:-1}"
REPEAT_RUNS="${REPEAT_RUNS:-2}"

CONCURRENCY_LIST="${CONCURRENCY_LIST:-1 4 16 64 128 256}"
RPS_LIST="${RPS_LIST:-2 5 10 20 40}"

mkdir -p "$ARTIFACT_ROOT"

cleanup() {
  pkill -9 -f "vllm-rs" >/dev/null 2>&1 || true
  pkill -9 -f "runner"  >/dev/null 2>&1 || true
  sleep 2
}

start_server() {
  local label="$1"; shift
  local extra=("$@")
  cleanup
  mkdir -p "$ARTIFACT_ROOT/$label"
  echo "[orchestrator] starting server $label (extra: ${extra[*]:-})"
  CUDA_COMPUTE_CAP=120 nohup "$BIN" --server \
    --m "$SERVED_MODEL" \
    --num-shards 4 --device-ids 0,1,2,3 \
    --max-model-len 4096 --max-num-seqs 128 \
    --port "$PORT" --dtype bf16 --seed 123 \
    --max-tokens 4096 \
    "${extra[@]}" \
    > "$ARTIFACT_ROOT/$label/server.log" 2>&1 &
  SERVER_PID=$!
  echo "[orchestrator] server pid=$SERVER_PID"

  for i in $(seq 1 90); do
    if curl -fsS "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
      echo "[orchestrator] $label ready after ${i}s"
      return 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "[orchestrator] $label server exited prematurely"
      tail -50 "$ARTIFACT_ROOT/$label/server.log" >&2
      return 1
    fi
    sleep 2
  done
  echo "[orchestrator] $label server never became ready"
  tail -50 "$ARTIFACT_ROOT/$label/server.log" >&2
  return 1
}

stop_server() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill -9 "$SERVER_PID" 2>/dev/null || true
  fi
  cleanup
}

run_cell() {
  local label="$1" mode="$2" param="$3" outfile="$4"
  local args=()
  if [[ "$mode" == "closed" ]]; then
    args=(--concurrency "$param" --request-rate 0)
  else
    args=(--concurrency 256 --request-rate "$param")
  fi
  echo "[orchestrator] $label cell $mode=$param -> $outfile"
  "${PYTHON:-/root/trtllm-venv/bin/python3}" /root/Documents/myelon-launch/vllm.rs/scripts/bench_stress_sharegpt.py \
    --url "http://127.0.0.1:$PORT" \
    --served-model-name "$SERVED_MODEL" \
    --tokenizer "$TOKENIZER" \
    --dataset "$DATASET" \
    --prompt-min-tok 800 --prompt-max-tok 1200 \
    --max-tokens 64 \
    --duration-sec "$DURATION_SEC" \
    --warmup-runs "$WARMUP_RUNS" --repeat-runs "$REPEAT_RUNS" \
    "${args[@]}" \
    --output-file "$outfile" \
    > "${outfile%.json}.client.log" 2>&1 || {
      echo "[orchestrator] WARN: $label $mode=$param failed (see ${outfile%.json}.client.log)"
    }
}

run_sweep_for() {
  local label="$1"; shift
  if ! start_server "$label" "$@"; then
    echo "[orchestrator] aborting $label"
    return 1
  fi
  for c in $CONCURRENCY_LIST; do
    run_cell "$label" closed "$c" "$ARTIFACT_ROOT/$label/closed_c${c}.json"
  done
  for r in $RPS_LIST; do
    run_cell "$label" open "$r" "$ARTIFACT_ROOT/$label/open_r${r}.json"
  done
  stop_server
}

trap cleanup EXIT

echo "===== socket ====="
run_sweep_for "socket" || true

echo "===== myelon_owned ====="
run_sweep_for "myelon_owned" --myelon-ipc --myelon-access-mode owned --myelon-backend shm || true

echo "===== myelon_typed ====="
run_sweep_for "myelon_typed" --myelon-ipc --myelon-access-mode typed --myelon-backend shm || true

echo "===== LATENCY-SWEEP-DONE ====="
