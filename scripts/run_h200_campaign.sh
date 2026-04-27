#!/usr/bin/env bash
# H200 campaign top-level driver — executes the RFC 0033 plan.
#
# Day 1 critical path:
#   Phase 1 / S-tp2 / 1k    (10 cells)  -> establishes socket baseline
#   Phase 2 / M-tp2 / 1k    (10 cells)  -> Myelon IPC over same workload
#   DECISION GATE
#
# If H1 reproduces → continue full campaign (Phase 2 widening + Phases 3, 4, 5).
# If H1 rejected → skip to Phase 3 (Myelon KV path) where Blackwell signal exists.

set -u

ART="${ART:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign}"
BIN_SOCKET="$ART/binaries/socket/vllm-rs"
BIN_RKYV="$ART/binaries/myelon-rkyv/vllm-rs"
BIN_FLATBUF="$ART/binaries/myelon-flatbuf/vllm-rs"
SWEEP=/root/Documents/myelon-launch/vllm.rs/scripts/run_h200_sweep.sh
PYTHON="${PYTHON:-/root/trtllm-venv/bin/python3}"

MODEL="${MODEL:-Qwen/Qwen3-30B-A3B}"
MODE="${MODE:-day1}"      # day1 | full | phase3-only

log() { echo "[campaign $(date +%H:%M:%S)] $*" | tee -a $ART/campaign.log; }

run_sweep() {
  # args: <bin> <phase> <cell> <topo> <bucket> [<myelon_ipc_flag> <pd_url>]
  local bin="$1" phase="$2" cell="$3" topo="$4" bucket="$5"
  local myelon_ipc="${6:-0}" pd_url="${7:-tcp://127.0.0.1:7000}"

  log ">>> sweep $cell @ $topo / $bucket (bin=$(basename $bin) myelon_ipc=$myelon_ipc pd_url=$pd_url)"
  BIN="$bin" ART="$ART" PHASE="$phase" CELL="$cell" TOPO="$topo" BUCKET="$bucket" \
    MYELON_IPC="$myelon_ipc" PD_URL="$pd_url" \
    bash $SWEEP 2>&1 | tee -a $ART/$phase/$cell.driver.log
  local rc=${PIPESTATUS[0]}
  log "<<< sweep $cell rc=$rc"
  return $rc
}

# Determine the Myelon win at a single concurrency by comparing cells across phases
compare_cell_throughput() {
  # args: <socket_cell_dir> <myelon_cell_dir>
  $PYTHON - "$1" "$2" <<'EOF'
import json, sys, glob, os
sock_dir, mye_dir = sys.argv[1], sys.argv[2]
def load(d):
    out = {}
    for p in sorted(glob.glob(f"{d}/closed_c*.json")):
        c = int(os.path.basename(p).replace("closed_c","").replace(".json",""))
        try:
            j = json.load(open(p))
        except: continue
        a = j.get("aggregate", {})
        rps = a.get("req_per_s", {})
        ttft = a.get("ttft_ms", {})
        sr = a.get("success_rate", {})
        out[c] = {
            "rps": rps.get("median") if isinstance(rps, dict) else rps,
            "ttft_p50": (ttft.get("p50") or {}).get("median"),
            "ttft_p99": (ttft.get("p99") or {}).get("median"),
            "success": sr.get("median") if isinstance(sr, dict) else sr,
        }
    return out
s, m = load(sock_dir), load(mye_dir)
print(f"{'C':>4} | {'sock req/s':>10} | {'mye req/s':>10} | {'Δ rps %':>8} | {'sock TTFT p50':>14} | {'mye TTFT p50':>14} | {'Δ TTFT %':>8}")
print("-"*92)
best_delta = -100
for c in sorted(set(s)|set(m)):
    sr = (s.get(c) or {}).get("rps")
    mr = (m.get(c) or {}).get("rps")
    sp = (s.get(c) or {}).get("ttft_p50")
    mp = (m.get(c) or {}).get("ttft_p50")
    drps = (mr-sr)/sr*100 if sr and mr else None
    dttft = (mp-sp)/sp*100 if sp and mp else None
    if drps is not None and drps > best_delta:
        best_delta = drps
    print(f"{c:>4} | {sr or '-':>10} | {mr or '-':>10} | {drps if drps is not None else '-':>8} | {sp or '-':>14} | {mp or '-':>14} | {dttft if dttft is not None else '-':>8}")
print()
print(f"BEST_RPS_DELTA_PCT={best_delta:.2f}")
EOF
}

# -------- Day 1 critical path --------
log "===== H200 CAMPAIGN START: mode=$MODE ====="
log "binaries: $(ls -1 $ART/binaries/ | tr '\n' ' ')"

if [ ! -f "$BIN_SOCKET" ] || [ ! -f "$BIN_RKYV" ]; then
  log "FATAL: required binaries missing"
  exit 1
fi

# Phase 1: socket baseline tp2 / 1k
run_sweep "$BIN_SOCKET" phase1_socket S-tp2 tp2 1k 0 || log "phase1 S-tp2 1k aborted"

# Phase 2: Myelon IPC tp2 / 1k
run_sweep "$BIN_RKYV"   phase2_myelon_ipc M-tp2 tp2 1k 1 tcp://127.0.0.1:7000 || log "phase2 M-tp2 1k aborted"

# DECISION GATE
log ""
log "==============================================================="
log "DAY 1 DECISION GATE — Phase 1 vs Phase 2 (tp2 / 1k)"
log "==============================================================="
GATE_OUTPUT=$(compare_cell_throughput "$ART/phase1_socket/S-tp2/1k" "$ART/phase2_myelon_ipc/M-tp2/1k" 2>&1)
echo "$GATE_OUTPUT" | tee -a $ART/decision_gate.log
log "$GATE_OUTPUT" >> $ART/campaign.log

best_delta=$(echo "$GATE_OUTPUT" | grep BEST_RPS_DELTA_PCT | sed 's/.*=//' | head -1)
log "Best Myelon RPS delta vs socket: ${best_delta}%"

if [ "$MODE" = "day1" ]; then
  log "MODE=day1: stopping after decision gate; review and decide next mode."
  exit 0
fi

# Branch: did H1 reproduce?
H1_CONFIRMED=$(awk "BEGIN { print (${best_delta:-0} >= 10.0) ? 1 : 0 }")
if [ "$H1_CONFIRMED" = "1" ]; then
  log "H1 CONFIRMED (best Myelon ≥ +10%). Continuing full campaign."

  # Phase 1 widening
  for cell_topo in "S-tp4 tp4" "S-pd1 pd1" "S-pd2 pd2"; do
    set -- $cell_topo
    run_sweep "$BIN_SOCKET" phase1_socket $1 $2 1k 0 || true
  done

  # Phase 2 widening
  for cell_topo in "M-tp4 tp4" "M-pd1 pd1" "M-pd2 pd2"; do
    set -- $cell_topo
    run_sweep "$BIN_RKYV" phase2_myelon_ipc $1 $2 1k 1 tcp://127.0.0.1:7000 || true
  done

  # 2k bucket on tp2 (the most-informative cell)
  run_sweep "$BIN_SOCKET" phase1_socket S-tp2 tp2 2k 0 || true
  run_sweep "$BIN_RKYV"   phase2_myelon_ipc M-tp2 tp2 2k 1 tcp://127.0.0.1:7000 || true
fi

# Phase 3: Myelon KV only (always run — Blackwell already showed signal)
log "===== Phase 3: Myelon KV ONLY (PD only) ====="
run_sweep "$BIN_RKYV" phase3_myelon_kv K-pd2 pd2 1k 0 myelon://default || true
run_sweep "$BIN_RKYV" phase3_myelon_kv K-pd1 pd1 1k 0 myelon://default || true

# Phase 4: Myelon both
log "===== Phase 4: Myelon BOTH (IPC + KV) ====="
run_sweep "$BIN_RKYV" phase4_myelon_both B-pd2 pd2 1k 1 myelon://default || true
run_sweep "$BIN_RKYV" phase4_myelon_both B-tp2 tp2 1k 1 || true

# Phase 5: codec shootout — pick winning cell from above (manual review for now)
log "===== Phase 5: codec shootout (skipped — needs manual cell choice from above) ====="

log "===== H200 CAMPAIGN COMPLETE ====="
