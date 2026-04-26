#!/usr/bin/env bash
# PD-mode latency sweep: 1K-token concurrency × RPS, Myelon-2MB vs TCP loopback.
# Launches a tp2/tp2 PD pair per transport, runs the same closed-loop concurrency
# sweep + open-loop RPS sweep we used for runner-IPC, kills the pair, moves on.

set -u

ARTIFACT_ROOT="${ARTIFACT_ROOT:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-26_pd_latency_sweep}"
BIN="${BIN:-/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs}"
DATASET="${DATASET:-/root/.cache/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json}"
TOKENIZER="${TOKENIZER:-Qwen/Qwen3-0.6B}"
SERVED_MODEL="${SERVED_MODEL:-Qwen/Qwen3-0.6B}"
PORT="${PORT:-8000}"
DURATION_SEC="${DURATION_SEC:-20}"
WARMUP_RUNS="${WARMUP_RUNS:-1}"
REPEAT_RUNS="${REPEAT_RUNS:-2}"

CONCURRENCY_LIST="${CONCURRENCY_LIST:-1 4 16 32 64}"
RPS_LIST="${RPS_LIST:-1 2 4 6}"

mkdir -p "$ARTIFACT_ROOT"

cleanup() {
  pkill -9 -f "vllm-rs" >/dev/null 2>&1 || true
  pkill -9 -f "runner"  >/dev/null 2>&1 || true
  sleep 2
  ls /dev/shm 2>/dev/null | grep vllm-rs-pd | xargs -r -I{} rm -f /dev/shm/{} || true
}

start_pd_pair() {
  local label="$1" pd_url="$2"
  cleanup
  mkdir -p "$ARTIFACT_ROOT/$label"
  echo "[orchestrator] starting PD pair $label (url=$pd_url)"

  CUDA_COMPUTE_CAP=120 RUST_MIN_STACK=33554432 nohup "$BIN" --pd-server --pd-url "$pd_url" \
    --m "$SERVED_MODEL" --num-shards 2 --device-ids 0,1 \
    --max-model-len 4096 --max-num-seqs 64 --dtype bf16 --seed 123 \
    > "$ARTIFACT_ROOT/$label/pd_server.log" 2>&1 &
  SERVER_PID=$!

  CUDA_COMPUTE_CAP=120 RUST_MIN_STACK=33554432 nohup "$BIN" --pd-client --pd-url "$pd_url" \
    --m "$SERVED_MODEL" --num-shards 2 --device-ids 2,3 \
    --max-model-len 4096 --max-num-seqs 64 --dtype bf16 --seed 123 \
    --server --port "$PORT" \
    > "$ARTIFACT_ROOT/$label/pd_client.log" 2>&1 &
  CLIENT_PID=$!

  echo "[orchestrator] server pid=$SERVER_PID client pid=$CLIENT_PID"

  for i in $(seq 1 90); do
    if curl -fsS "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
      echo "[orchestrator] $label PD ready after ${i}s"
      return 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null && ! kill -0 "$CLIENT_PID" 2>/dev/null; then
      echo "[orchestrator] $label PD pair exited prematurely"
      tail -30 "$ARTIFACT_ROOT/$label/pd_server.log" "$ARTIFACT_ROOT/$label/pd_client.log" >&2 2>/dev/null
      return 1
    fi
    sleep 2
  done
  echo "[orchestrator] $label PD pair never became ready"
  return 1
}

stop_pd_pair() {
  if [[ -n "${SERVER_PID:-}" ]]; then kill -9 "$SERVER_PID" 2>/dev/null || true; fi
  if [[ -n "${CLIENT_PID:-}" ]]; then kill -9 "$CLIENT_PID" 2>/dev/null || true; fi
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
  /root/trtllm-venv/bin/python3 /root/Documents/myelon-launch/vllm.rs/scripts/bench_stress_sharegpt.py \
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
  local label="$1" pd_url="$2"
  if ! start_pd_pair "$label" "$pd_url"; then
    echo "[orchestrator] aborting $label"
    return 1
  fi
  for c in $CONCURRENCY_LIST; do
    run_cell "$label" closed "$c" "$ARTIFACT_ROOT/$label/closed_c${c}.json"
  done
  for r in $RPS_LIST; do
    run_cell "$label" open "$r" "$ARTIFACT_ROOT/$label/open_r${r}.json"
  done
  stop_pd_pair
}

trap cleanup EXIT

echo "===== myelon_2mb ====="
run_sweep_for "myelon_2mb" "myelon://default" || true

echo "===== tcp_loopback ====="
run_sweep_for "tcp_loopback" "tcp://127.0.0.1:7000" || true

echo "===== PD-LATENCY-SWEEP-DONE ====="
