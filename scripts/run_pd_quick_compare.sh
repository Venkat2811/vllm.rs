#!/usr/bin/env bash
# Quick PD compare: c=1 + c=8 closed-loop, two transports, ~6 min total.

set -u

ARTIFACT="${ARTIFACT:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-26_pd_latency_sweep}"
BIN="${BIN:-/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs}"
DATASET="${DATASET:-/root/.cache/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json}"
PORT=8000

cleanup() {
  pkill -9 -f "vllm-rs" >/dev/null 2>&1 || true
  pkill -9 -f "runner"  >/dev/null 2>&1 || true
  sleep 2
  ls /dev/shm 2>/dev/null | grep vllm-rs-pd | xargs -r -I{} rm -f /dev/shm/{} || true
}

run_variant() {
  local label="$1" pd_url="$2"
  cleanup
  mkdir -p "$ARTIFACT/$label"
  echo "===== $label (url=$pd_url) ====="

  CUDA_COMPUTE_CAP=120 RUST_MIN_STACK=33554432 nohup "$BIN" --pd-server --pd-url "$pd_url" \
    --m Qwen/Qwen3-0.6B --num-shards 2 --device-ids 0,1 \
    --max-model-len 4096 --max-num-seqs 64 --dtype bf16 --seed 123 \
    > "$ARTIFACT/$label/pd_server.log" 2>&1 &
  CUDA_COMPUTE_CAP=120 RUST_MIN_STACK=33554432 nohup "$BIN" --pd-client --pd-url "$pd_url" \
    --m Qwen/Qwen3-0.6B --num-shards 2 --device-ids 2,3 \
    --max-model-len 4096 --max-num-seqs 64 --dtype bf16 --seed 123 \
    --server --port "$PORT" \
    > "$ARTIFACT/$label/pd_client.log" 2>&1 &

  for i in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
      echo "[orchestrator] $label PD ready after ${i}s"; break
    fi
    sleep 2
  done

  for c in 1 8; do
    echo "[orchestrator] $label cell c=$c"
    /root/trtllm-venv/bin/python3 /root/Documents/myelon-launch/vllm.rs/scripts/bench_stress_sharegpt.py \
      --url "http://127.0.0.1:$PORT" \
      --served-model-name Qwen/Qwen3-0.6B \
      --tokenizer Qwen/Qwen3-0.6B \
      --dataset "$DATASET" \
      --prompt-min-tok 800 --prompt-max-tok 1200 \
      --max-tokens 64 \
      --duration-sec 20 \
      --warmup-runs 1 --repeat-runs 2 \
      --concurrency "$c" --request-rate 0 \
      --output-file "$ARTIFACT/$label/closed_c${c}.json" \
      > "$ARTIFACT/$label/closed_c${c}.client.log" 2>&1 || \
        echo "[orchestrator] WARN: $label c=$c failed"
  done

  cleanup
}

trap cleanup EXIT
run_variant myelon_2mb "myelon://default" || true
run_variant tcp_loopback "tcp://127.0.0.1:7000" || true
echo "===== QUICK-COMPARE-DONE ====="
