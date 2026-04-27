#!/usr/bin/env bash
# Re-run just the 1k bucket of Phase 8 (failed in original run due to OOM
# race when MAX_NUM_SEQS was being bumped down).

ART="${ART:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign}"
SWEEP=/root/Documents/myelon-launch/vllm.rs/scripts/run_h200_sweep.sh

export MAX_MODEL_LEN=16384
export MAX_NUM_SEQS=128
export MAX_TOKENS=256
export NUM_REQUESTS=80
export WARMUP_RUNS=1
export REPEAT_RUNS=1
export CONCURRENCY_LIST="4 16 64 128 256"
export ART="$ART"

log() { echo "[push-1k $(date +%H:%M:%S)] $*" | tee -a $ART/push_30b_1k_retry.log; }

# Wipe old failed dirs from prior aborted runs
rm -rf $ART/phase8_push_30b/S-tp2/1k $ART/phase8_push_30b/M-tp2/1k 2>/dev/null

log "===== 1k bucket retry start ====="
log "MAX_MODEL_LEN=$MAX_MODEL_LEN MAX_NUM_SEQS=$MAX_NUM_SEQS MAX_TOKENS=$MAX_TOKENS"

log ">>> S-tp2 / 1k"
BIN=$ART/binaries/socket/vllm-rs PHASE=phase8_push_30b CELL=S-tp2 TOPO=tp2 BUCKET=1k MYELON_IPC=0 \
  bash $SWEEP > $ART/phase8_push_30b/S-tp2-1k.driver.log 2>&1
log "<<< S-tp2 rc=$?"

log ">>> M-tp2 / 1k"
BIN=$ART/binaries/myelon-rkyv/vllm-rs PHASE=phase8_push_30b CELL=M-tp2 TOPO=tp2 BUCKET=1k MYELON_IPC=1 \
  bash $SWEEP > $ART/phase8_push_30b/M-tp2-1k.driver.log 2>&1
log "<<< M-tp2 rc=$?"

log "===== 1k bucket retry DONE ====="
