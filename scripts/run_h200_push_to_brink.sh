#!/usr/bin/env bash
# H200 push-to-brink — re-run 30B-A3B (and optionally 122B-A10B) with workload
# settings that actually pressure the system: longer context, longer decode,
# higher concurrency, 2k token prompts.
#
# Reasoning: the prior H200 campaign used max-model-len=4096, max-tokens=64,
# c-stop at 128. Memory used ~50/143 GB per GPU = 35% utilization. Decode
# was ~3% of wall time. That's not a meaningful test for IPC-layer effects.

ART="${ART:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign}"
SWEEP=/root/Documents/myelon-launch/vllm.rs/scripts/run_h200_sweep.sh
BIN_SOCKET="$ART/binaries/socket/vllm-rs"
BIN_RKYV="$ART/binaries/myelon-rkyv/vllm-rs"

# Push-to-brink settings — override sweep defaults
export MAX_MODEL_LEN=16384       # 4× longer context
export MAX_NUM_SEQS=128          # 16K × 256 batch OOMs at 196 GB / 106 GB avail; back off to 128
export MAX_TOKENS=256            # 4× longer decode (real load)
export NUM_REQUESTS=80
export WARMUP_RUNS=1
export REPEAT_RUNS=1
export CONCURRENCY_LIST="4 16 64 128 256"   # skip c=1 (too slow at long decode); push past 128
export ART="$ART"

mkdir -p $ART/phase8_push_30b
log() { echo "[push $(date +%H:%M:%S)] $*" | tee -a $ART/push_30b.log; }

run() {
  local bin="$1" cell="$2" topo="$3" bucket="$4" mi="$5" pdu="${6:-tcp://127.0.0.1:7000}"
  log ">>> $cell @ $topo / $bucket (bin=$(basename $(dirname $bin)) myelon_ipc=$mi)"
  BIN="$bin" PHASE="phase8_push_30b" CELL="$cell" TOPO="$topo" BUCKET="$bucket" \
    MYELON_IPC="$mi" PD_URL="$pdu" \
    bash $SWEEP > $ART/phase8_push_30b/$cell-$bucket.driver.log 2>&1
  local rc=$?
  log "<<< $cell rc=$rc"
}

log "===== H200 push-to-brink: 30B-A3B tp2 ====="
log "MAX_MODEL_LEN=$MAX_MODEL_LEN MAX_TOKENS=$MAX_TOKENS MAX_NUM_SEQS=$MAX_NUM_SEQS"
log "NUM_REQUESTS=$NUM_REQUESTS  CONCURRENCY_LIST=$CONCURRENCY_LIST"

# 1k bucket
run "$BIN_SOCKET" S-tp2 tp2 1k 0
run "$BIN_RKYV"   M-tp2 tp2 1k 1

# 2k bucket — longer prompts pressure prefill IPC payload size
run "$BIN_SOCKET" S-tp2 tp2 2k 0
run "$BIN_RKYV"   M-tp2 tp2 2k 1

log "===== H200 push-to-brink DONE ====="
