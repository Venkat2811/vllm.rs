#!/usr/bin/env bash
# H200 campaign sweep orchestrator.
#
# Runs one (binary, topology, bucket) cell-set: starts the vllm-rs server (or PD
# pair), runs the concurrency sweep (default 1,5,10,20,30,40,50,75,100,150),
# kills the server, exits. Stops the sweep early on first cell with
# success_rate < SUCCESS_FLOOR.
#
# Cells go to: $ART/<phase_label>/<cell_id>/closed_c<C>.json
# Server log:  $ART/<phase_label>/<cell_id>/server.log [+ pd_client.log for PD]
#
# Usage examples:
#   BIN=$ART/binaries/vllm-rs-socket          PHASE=phase1_socket       CELL=S-tp2  TOPO=tp2 BUCKET=1k bash run_h200_sweep.sh
#   BIN=$ART/binaries/vllm-rs-myelon-rkyv     PHASE=phase2_myelon_ipc   CELL=M-tp2  TOPO=tp2 BUCKET=1k MYELON_IPC=1 bash run_h200_sweep.sh
#   BIN=$ART/binaries/vllm-rs-myelon-rkyv     PHASE=phase4_myelon_both  CELL=B-pd2  TOPO=pd2 BUCKET=1k MYELON_IPC=1 PD_URL=myelon://default bash run_h200_sweep.sh

# -------- inputs (env-driven) --------
BIN="${BIN:?BIN= path to vllm-rs binary required}"
ART="${ART:-/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign}"
PHASE="${PHASE:?PHASE= e.g. phase1_socket required}"
CELL="${CELL:?CELL= e.g. S-tp2 required}"
TOPO="${TOPO:?TOPO= one of: tp2 tp4 pd1 pd2 required}"
BUCKET="${BUCKET:-1k}"               # 1k or 2k

MODEL="${MODEL:-Qwen/Qwen3-30B-A3B}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-128}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
MAX_TOKENS="${MAX_TOKENS:-64}"
NUM_REQUESTS="${NUM_REQUESTS:-200}"
WARMUP_RUNS="${WARMUP_RUNS:-1}"
REPEAT_RUNS="${REPEAT_RUNS:-3}"
PORT="${PORT:-8000}"
PD_PORT="${PD_PORT:-7000}"
SUCCESS_FLOOR="${SUCCESS_FLOOR:-0.95}"
CONCURRENCY_LIST="${CONCURRENCY_LIST:-1 5 10 20 30 40 50 75 100 150}"

# Transport flags
MYELON_IPC="${MYELON_IPC:-0}"        # 1 → add --myelon-ipc
PD_URL="${PD_URL:-tcp://127.0.0.1:$PD_PORT}"     # for pd1/pd2 — myelon://default to use Myelon SHM KV
DTYPE="${DTYPE:-bf16}"
SEED="${SEED:-123}"

# Bench flags
BENCH_PROMPTS="$ART/datasets/sharegpt_${BUCKET}.jsonl"
BENCH="/root/Documents/myelon-launch/vllm.rs/scripts/bench_stress_sharegpt.py"
PYTHON="${PYTHON:-/root/trtllm-venv/bin/python3}"
GOODPUT="${GOODPUT:---goodput ttft:1000 --goodput tpot:100 --goodput e2e:5000}"

OUTDIR="$ART/$PHASE/$CELL/$BUCKET"
mkdir -p "$OUTDIR"

# -------- helpers --------
log()  { echo "[orchestrator $(date +%H:%M:%S)] $*"; }
warn() { echo "[orchestrator $(date +%H:%M:%S)] WARN: $*" >&2; }

cleanup() {
  bash /root/Documents/myelon-launch/vllm.rs/scripts/cleanup_h200.sh
}

start_server_tp() {
  # Single-engine TP topology
  local devices flags
  case "$TOPO" in
    tp2) devices="0,1" ;;
    tp4) devices="0,1,2,3" ;;
    *)   echo "TOPO=$TOPO not single-engine; use start_server_pd"; return 2 ;;
  esac
  flags=""
  [ "$MYELON_IPC" = "1" ] && flags="--myelon-ipc"
  log "starting tp $TOPO server on GPUs $devices myelon_ipc=$MYELON_IPC"
  CUDA_COMPUTE_CAP=90 RUST_MIN_STACK=33554432 nohup "$BIN" --server \
    --m "$MODEL" --d "$devices" --num-shards $(echo "$devices" | tr ',' '\n' | wc -l) \
    --max-num-seqs "$MAX_NUM_SEQS" --max-model-len "$MAX_MODEL_LEN" \
    --max-tokens 4096 --dtype "$DTYPE" --seed "$SEED" \
    --port "$PORT" --prefix-cache \
    $flags \
    > "$OUTDIR/../server.log" 2>&1 &
  SERVER_PID=$!
  log "server pid=$SERVER_PID"
}

start_server_pd() {
  # PD pair (server engine + client engine)
  local s_devices c_devices
  case "$TOPO" in
    pd1) s_devices="0";   c_devices="1"   ;;
    pd2) s_devices="0,1"; c_devices="2,3" ;;
    *)   echo "TOPO=$TOPO not PD"; return 2 ;;
  esac
  local flags=""
  [ "$MYELON_IPC" = "1" ] && flags="--myelon-ipc"

  log "starting PD: server GPUs $s_devices, client GPUs $c_devices, pd-url=$PD_URL myelon_ipc=$MYELON_IPC"
  CUDA_COMPUTE_CAP=90 RUST_MIN_STACK=33554432 nohup "$BIN" --pd-server --pd-url "$PD_URL" \
    --m "$MODEL" --d "$s_devices" --num-shards $(echo "$s_devices" | tr ',' '\n' | wc -l) \
    --max-num-seqs "$MAX_NUM_SEQS" --max-model-len "$MAX_MODEL_LEN" \
    --dtype "$DTYPE" --seed "$SEED" --prefix-cache \
    $flags \
    > "$OUTDIR/../pd_server.log" 2>&1 &
  PD_SERVER_PID=$!
  CUDA_COMPUTE_CAP=90 RUST_MIN_STACK=33554432 nohup "$BIN" --pd-client --pd-url "$PD_URL" \
    --m "$MODEL" --d "$c_devices" --num-shards $(echo "$c_devices" | tr ',' '\n' | wc -l) \
    --max-num-seqs "$MAX_NUM_SEQS" --max-model-len "$MAX_MODEL_LEN" \
    --dtype "$DTYPE" --seed "$SEED" --prefix-cache \
    --server --port "$PORT" \
    $flags \
    > "$OUTDIR/../pd_client.log" 2>&1 &
  PD_CLIENT_PID=$!
  SERVER_PID=$PD_CLIENT_PID  # for stop_server
  log "pd_server pid=$PD_SERVER_PID  pd_client pid=$PD_CLIENT_PID"
}

wait_for_ready() {
  local max=600  # 10 min for big-model startup
  for i in $(seq 1 $max); do
    if curl -fsS "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
      log "server READY in ${i}s"
      return 0
    fi
    if [ -n "${PD_SERVER_PID:-}" ] && ! kill -0 "$PD_SERVER_PID" 2>/dev/null; then
      warn "pd_server died before ready"
      return 1
    fi
    if [ -n "${PD_CLIENT_PID:-}" ] && ! kill -0 "$PD_CLIENT_PID" 2>/dev/null; then
      warn "pd_client died before ready"
      return 1
    fi
    if [ -z "${PD_SERVER_PID:-}" ] && ! kill -0 "$SERVER_PID" 2>/dev/null; then
      warn "server died before ready"
      return 1
    fi
    sleep 2
  done
  warn "server never became ready in ${max}s"
  return 1
}

stop_server() {
  for pid in "${SERVER_PID:-}" "${PD_SERVER_PID:-}" "${PD_CLIENT_PID:-}"; do
    [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null || true
  done
  cleanup
}

run_cell() {
  local C="$1" outfile="$OUTDIR/closed_c${C}.json"
  log "cell C=$C -> $outfile"
  $PYTHON $BENCH \
    --url "http://127.0.0.1:$PORT" \
    --served-model-name "$MODEL" \
    --prompts-file "$BENCH_PROMPTS" \
    --max-tokens "$MAX_TOKENS" \
    --num-requests "$NUM_REQUESTS" \
    --max-concurrency "$C" \
    --request-rate inf \
    --warmup-runs "$WARMUP_RUNS" --repeat-runs "$REPEAT_RUNS" \
    $GOODPUT \
    --output-file "$outfile" \
    > "${outfile%.json}.client.log" 2>&1
  local rc=$?
  # Check success rate to decide whether to continue sweep
  local sr
  sr=$($PYTHON -c "
import json, sys
try:
    d = json.load(open('$outfile'))
    a = d.get('aggregate', {})
    sr_field = a.get('success_rate', {})
    if isinstance(sr_field, dict):
        print(sr_field.get('median', 0))
    else:
        print(sr_field or 0)
except Exception as e:
    print(0)
" 2>/dev/null || echo 0)
  log "cell C=$C done rc=$rc success_rate=$sr"
  # Compare via awk (bash can't do float comparison directly)
  if awk "BEGIN { exit !($sr < $SUCCESS_FLOOR) }"; then
    warn "success_rate $sr < $SUCCESS_FLOOR — stopping sweep"
    return 1
  fi
  return 0
}

# -------- main --------
trap cleanup EXIT INT TERM
cleanup

case "$TOPO" in
  tp2|tp4) start_server_tp || exit 1 ;;
  pd1|pd2) start_server_pd || exit 1 ;;
  *) echo "unknown TOPO=$TOPO"; exit 2 ;;
esac

if ! wait_for_ready; then
  warn "aborting cell — server didn't come up"
  stop_server
  exit 1
fi

ABORTED=0
for C in $CONCURRENCY_LIST; do
  if ! run_cell "$C"; then
    ABORTED=1
    break
  fi
done

stop_server
log "===== SWEEP DONE phase=$PHASE cell=$CELL bucket=$BUCKET aborted=$ABORTED ====="
