#!/usr/bin/env bash
# Phase 8.6 — tp4 push-to-brink on Qwen3-30B-A3B.
#
# Why this matters: at tp=4 the broadcast fan-out is to 4 runners (vs 2 at tp2).
# Socket path = 4 sequential socket writes per request (rayon-per-rank fan-out).
# Myelon path = 1 RPC ring write + 4 reads.
# The socket-vs-Myelon overhead delta scales with rank count.
#
# Memory math (30B-A3B at tp4):
#   Weights:  ~57 GB / 4 = 14 GB / GPU
#   KV avail: 141 - 14 = 127 GB / GPU × 4 = 508 GB total
#   Per-token KV at tp4: ~25 KB (half of tp2's 50 KB; layers split 4 ways)
#   At max-num-seqs=256, max-model-len=32768:
#     256 × 32K × 25 KB = 200 GB → fits in 508 GB total

ART="${ART:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign}"
SWEEP=/root/Documents/myelon-launch/vllm.rs/scripts/run_h200_sweep.sh

export MAX_MODEL_LEN=32768       # 2× longer context than Phase 8 (tp4 has more KV room)
export MAX_NUM_SEQS=256          # 2× batching (KV math fits at tp4)
export MAX_TOKENS=512            # 2× decode load
export NUM_REQUESTS=80
export WARMUP_RUNS=1
export REPEAT_RUNS=1
export CONCURRENCY_LIST="4 16 64 128 256 512"   # push past tp2's c=256
export ART="$ART"

mkdir -p $ART/phase8_6_push_tp4
log() { echo "[push-tp4 $(date +%H:%M:%S)] $*" | tee -a $ART/push_tp4.log; }

run() {
  local bin="$1" cell="$2" topo="$3" bucket="$4" mi="$5"
  log ">>> $cell @ $topo / $bucket (bin=$(basename $(dirname $bin)) myelon_ipc=$mi)"
  BIN="$bin" PHASE="phase8_6_push_tp4" CELL="$cell" TOPO="$topo" BUCKET="$bucket" \
    MYELON_IPC="$mi" \
    bash $SWEEP > $ART/phase8_6_push_tp4/$cell-$bucket.driver.log 2>&1
  log "<<< $cell rc=$?"
}

log "===== Phase 8.6: 30B-A3B tp4 push-to-brink ====="
log "MAX_MODEL_LEN=$MAX_MODEL_LEN MAX_TOKENS=$MAX_TOKENS MAX_NUM_SEQS=$MAX_NUM_SEQS"
log "CONCURRENCY_LIST=$CONCURRENCY_LIST"

# 1k bucket only — tp4 broadcast cost is the variable; bucket size matters less here
run "$ART/binaries/socket/vllm-rs"      S-tp4 tp4 1k 0
run "$ART/binaries/myelon-rkyv/vllm-rs" M-tp4 tp4 1k 1

# 2k bucket if 1k surfaces signal — the bigger prompts amplify any RunPrefill broadcast cost
run "$ART/binaries/socket/vllm-rs"      S-tp4 tp4 2k 0
run "$ART/binaries/myelon-rkyv/vllm-rs" M-tp4 tp4 2k 1

log "===== Phase 8.6 DONE ====="
