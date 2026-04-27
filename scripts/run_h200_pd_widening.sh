#!/usr/bin/env bash
# H200 PD widening — Phases 1, 2, 3, 4 on pd2 topology.
# Built post-Day1 since Day 1 showed only +3.3% on tp2 (below H1 +10% bar).
# Hypothesis: PD KV transfer path will show stronger signal (per Blackwell +7% at c=8).

ART="${ART:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign}"
SWEEP=/root/Documents/myelon-launch/vllm.rs/scripts/run_h200_sweep.sh
BIN_SOCKET="$ART/binaries/socket/vllm-rs"
BIN_RKYV="$ART/binaries/myelon-rkyv/vllm-rs"

export NUM_REQUESTS=50
export WARMUP_RUNS=1
export REPEAT_RUNS=1
export CONCURRENCY_LIST="1 8 32 64 128"
export ART="$ART"

log() { echo "[pd-widening $(date +%H:%M:%S)] $*" | tee -a $ART/pd_widening.log; }

run() {
  # args: <bin> <phase> <cell> <topo> <bucket> <myelon_ipc> <pd_url>
  local bin="$1" phase="$2" cell="$3" topo="$4" bucket="$5" mi="$6" pdu="$7"
  log ">>> $cell @ $topo / $bucket (myelon_ipc=$mi pd_url=$pdu)"
  BIN="$bin" PHASE="$phase" CELL="$cell" TOPO="$topo" BUCKET="$bucket" \
    MYELON_IPC="$mi" PD_URL="$pdu" \
    bash $SWEEP > $ART/$phase/$cell.driver.log 2>&1
  local rc=$?
  log "<<< $cell rc=$rc"
}

log "===== H200 PD widening start ====="

# Phase 1: socket baseline on PD topologies
run "$BIN_SOCKET" phase1_socket S-pd2 pd2 1k 0 tcp://127.0.0.1:7000

# Phase 2: Myelon IPC + TCP KV
run "$BIN_RKYV"   phase2_myelon_ipc M-pd2 pd2 1k 1 tcp://127.0.0.1:7000

# Phase 3: socket IPC + Myelon KV
run "$BIN_RKYV"   phase3_myelon_kv  K-pd2 pd2 1k 0 myelon://default

# Phase 4: Myelon IPC + Myelon KV
run "$BIN_RKYV"   phase4_myelon_both B-pd2 pd2 1k 1 myelon://default

log "===== H200 PD widening DONE ====="
