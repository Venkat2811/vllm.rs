#!/usr/bin/env bash
# v2: smart early-bail version of mac_pd_long_ctx_bench.sh.
#
# Heuristics added on top of v1:
#
# 1. **Per-bucket socket gate.** Run `pd_socket` first for each ctx bucket.
#    If socket success rate < $MIN_SUCCESS_FOR_TYPED_TCP (default 30%):
#      - SKIP `pd_myelon_typed` for this bucket (TCP-loopback bottleneck same as
#        socket; it will fail similarly. Wastes ~10-15 min per skipped cell.)
#      - STILL run `pd_myelon_typed_kv` (Myelon SHM might escape the bottleneck).
#
# 2. **Per-bucket KV-myelon gate.** If `pd_myelon_typed_kv` for this ctx
#    also gets <$MIN_SUCCESS_FOR_NEXT_BUCKET (default 30%):
#      - SKIP all REMAINING (larger) ctx buckets — past the operating envelope.
#      - The remaining cells would all fail similarly; bench loop exits early.
#
# 3. **Quick smoke probe.** First request after server boot: send 1 req, time it.
#    If TTFT > $SMOKE_TIMEOUT_MS (default 90000 ms ≈ 90s), the cell is hopeless —
#    abort the cell early instead of waiting for the full bench client to time
#    out 20× the same way.
#
# Override env vars:
#   MIN_SUCCESS_FOR_TYPED_TCP=30   (percent; <30 → skip myelon-typed-KVtcp)
#   MIN_SUCCESS_FOR_NEXT_BUCKET=30 (percent; <30 → skip larger buckets)
#   SMOKE_TIMEOUT_MS=90000         (ms; >this on first req → abort cell)
#   SKIP_SMOKE_PROBE=1             (disable heuristic 3)
#   FORCE_ALL_CELLS=1              (disable all early-bail; runs every cell)
#
# Usage and expected savings:
#   On a sweep where ctx=8k is past envelope, v1 wastes ~30 min running
#   3 cells × 6-10 min that all fail 0%. v2 skips them after the first
#   socket cell shows <30% success.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/cleanup_mac_bench.sh"

BIN=./target/release/vllm-rs
MODEL=${MODEL:-Qwen/Qwen3-4B}
NUM_REQS=${NUM_REQS:-30}
CONCURRENCY=${CONCURRENCY:-4}
MAX_TOKENS=${MAX_TOKENS:-128}
CTX_BUCKETS=${CTX_BUCKETS:-"4096 8192 16384"}

# Smart-skip thresholds (override via env)
MIN_SUCCESS_FOR_TYPED_TCP=${MIN_SUCCESS_FOR_TYPED_TCP:-30}
MIN_SUCCESS_FOR_NEXT_BUCKET=${MIN_SUCCESS_FOR_NEXT_BUCKET:-30}
SMOKE_TIMEOUT_MS=${SMOKE_TIMEOUT_MS:-90000}
SKIP_SMOKE_PROBE=${SKIP_SMOKE_PROBE:-0}
FORCE_ALL_CELLS=${FORCE_ALL_CELLS:-0}

MAX_BUCKET=$(echo "$CTX_BUCKETS" | tr ' ' '\n' | sort -n | tail -1)
MAXLEN=$(( (MAX_BUCKET * 6 / 5 + MAX_TOKENS + 1023) / 1024 * 1024 ))

for p in 18000 19000 20000 21000 22000 23000; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { HTTP_S=$p; break; }
done
for p in 18001 19001 20001 21001 22001 23001; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { PD_PORT=$p; break; }
done
for p in 18002 19002 20002 21002 22002 23002; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { HTTP_C=$p; break; }
done

OUT_DIR="$ROOT/scripts/mac_pd_long_ctx_v2_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Model: $MODEL  reqs/cell: $NUM_REQS  concurrency: $CONCURRENCY  max_tokens: $MAX_TOKENS"
echo "Buckets: $CTX_BUCKETS  max_model_len: $MAXLEN"
echo "Smart-skip: MIN_SOCKET_SUCCESS_FOR_TYPED_TCP=${MIN_SUCCESS_FOR_TYPED_TCP}%  MIN_KV_SUCCESS_FOR_NEXT_BUCKET=${MIN_SUCCESS_FOR_NEXT_BUCKET}%  SMOKE_TIMEOUT=${SMOKE_TIMEOUT_MS}ms"
echo "Ports: srv=$HTTP_S pd=$PD_PORT cli=$HTTP_C"
echo "Artifacts: $OUT_DIR"
echo ""

# Read success rate (0..100) from a finished cell's _results.json
read_success_pct() {
    local label="$1"
    python3 - <<PYEOF
import json, sys
try:
    d = json.load(open("$OUT_DIR/${label}_results.json"))
    sr = d.get("aggregate", {}).get("success_rate", {}).get("median")
    print(int((sr or 0) * 100))
except Exception:
    print(0)
PYEOF
}

# Run a single cell. Returns 0 on success, non-zero on failure.
# If first-request smoke probe times out and SKIP_SMOKE_PROBE != 1, abort the cell.
run_cell() {
    local label="$1" pd_url="$2" prompts_file="$3"; shift 3
    local extra=("$@")
    cleanup_between_cells "$HTTP_C"

    local mns=$((CONCURRENCY * 2))
    [[ $mns -lt 4 ]] && mns=4

    "$BIN" --pd-server --port $HTTP_S --m $MODEL --d 0 \
        --max-model-len $MAXLEN --max-num-seqs $mns --pd-url "$pd_url" \
        "${extra[@]}" > "$OUT_DIR/${label}_server.log" 2>&1 &
    SERVER_PID=$!

    "$BIN" --server --pd-client --port $HTTP_C --m $MODEL --d 0 \
        --max-model-len $MAXLEN --max-num-seqs $mns --pd-url "$pd_url" \
        "${extra[@]}" > "$OUT_DIR/${label}_client.log" 2>&1 &
    CLIENT_PID=$!

    for i in $(seq 1 180); do
        curl -sf http://127.0.0.1:$HTTP_C/v1/models >/dev/null 2>&1 && break
        sleep 1
    done
    if ! curl -sf http://127.0.0.1:$HTTP_C/v1/models >/dev/null 2>&1; then
        echo "  ❌ ${label} client did not come up"
        kill $SERVER_PID $CLIENT_PID 2>/dev/null
        return 1
    fi

    # Smoke probe: send 1 small request, time it. If it exceeds SMOKE_TIMEOUT_MS,
    # the cell is hopeless and we abort early.
    if [[ "$SKIP_SMOKE_PROBE" != "1" && "$FORCE_ALL_CELLS" != "1" ]]; then
        local probe_prompt; probe_prompt=$(head -1 "$prompts_file" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['prompt'][:400])" 2>/dev/null)
        local probe_start; probe_start=$(python3 -c 'import time; print(int(time.time()*1000))')
        local probe_timeout_s=$(( SMOKE_TIMEOUT_MS / 1000 + 5 ))
        local probe_body; probe_body=$(P="$probe_prompt" python3 -c "import json,os; print(json.dumps({'model':'qwen3','messages':[{'role':'user','content':os.environ['P']}],'max_tokens':8}))")
        if ! timeout ${probe_timeout_s} curl -sf -X POST "http://127.0.0.1:$HTTP_C/v1/chat/completions" \
              -H 'Content-Type: application/json' \
              -d "$probe_body" \
              >/dev/null 2>&1; then
            local probe_elapsed=$(( $(python3 -c 'import time; print(int(time.time()*1000))') - probe_start ))
            echo "  ⚠️  ${label} smoke probe timed out (~${probe_elapsed}ms > ${SMOKE_TIMEOUT_MS}ms threshold)"
            echo "  ⚠️  Aborting cell early to save bench wall time"
            kill $SERVER_PID $CLIENT_PID 2>/dev/null
            sleep 2
            cleanup_between_cells "$HTTP_C"
            # Write a stub results.json so the aggregator sees the cell as 0%
            python3 - <<PYEOF > "$OUT_DIR/${label}_results.json"
import json
print(json.dumps({"aborted_by_smoke_probe": True, "aggregate": {"success_rate": {"median": 0.0}, "req_per_s": {"median": 0.0}}}))
PYEOF
            return 2
        fi
    fi

    uv run --with aiohttp --with transformers python3 \
        "$SCRIPT_DIR/bench_stress_sharegpt.py" \
        --url "http://127.0.0.1:$HTTP_C" \
        --served-model-name qwen3 \
        --prompts-file "$prompts_file" \
        --max-tokens $MAX_TOKENS \
        --concurrency $CONCURRENCY \
        --num-requests $NUM_REQS \
        --output-file "$OUT_DIR/${label}_results.json" \
        --no-stream \
        > "$OUT_DIR/${label}_bench.log" 2>&1
    local rc=$?

    kill $SERVER_PID $CLIENT_PID 2>/dev/null
    sleep 2
    cleanup_between_cells "$HTTP_C"
    return $rc
}

skip_remaining_buckets=0

for ctx in $CTX_BUCKETS; do
    if [[ $skip_remaining_buckets -eq 1 ]]; then
        echo "═══ SKIPPING ctx=${ctx} (prior bucket past envelope) ═══"
        continue
    fi

    PROMPTS="$ROOT/scripts/long_ctx_buckets/sharegpt_${ctx}.jsonl"
    if [[ ! -f "$PROMPTS" ]]; then
        echo "❌ missing $PROMPTS — run build_long_context_buckets.py first"
        exit 1
    fi
    echo "═══ ctx=${ctx} ═══"

    # Cell 1: pd_socket (always run; gates the next two cells)
    echo "── pd_socket (KV=tcp) ──"
    run_cell "ctx${ctx}_socket" "tcp://127.0.0.1:$PD_PORT" "$PROMPTS" --force-runner || echo "  socket cell failed"
    socket_pct=$(read_success_pct "ctx${ctx}_socket")
    echo "  → socket success: ${socket_pct}%"
    echo ""

    # Cell 2: pd_myelon_typed (KV=tcp). Skip if socket already showed TCP-loopback bottleneck.
    if [[ $socket_pct -lt $MIN_SUCCESS_FOR_TYPED_TCP && "$FORCE_ALL_CELLS" != "1" ]]; then
        echo "── pd_myelon_typed (KV=tcp) — SKIPPED (socket success ${socket_pct}% < ${MIN_SUCCESS_FOR_TYPED_TCP}%) ──"
        # Write a stub so aggregate doesn't choke
        python3 - <<PYEOF > "$OUT_DIR/ctx${ctx}_myelon_typed_results.json"
import json
print(json.dumps({"skipped_due_to_socket_failure": True, "aggregate": {"success_rate": {"median": 0.0}, "req_per_s": {"median": 0.0}}}))
PYEOF
        echo ""
    else
        echo "── pd_myelon_typed (KV=tcp) ──"
        run_cell "ctx${ctx}_myelon_typed" "tcp://127.0.0.1:$PD_PORT" "$PROMPTS" \
            --force-runner --myelon-ipc --myelon-access-mode typed || echo "  myelon_typed cell failed"
        echo ""
    fi

    # Cell 3: pd_myelon_typed_kv (full Myelon SHM). Always run — this is where
    # the bandwidth-bound regime might escape the TCP-loopback bottleneck.
    echo "── pd_myelon_typed_kv (KV=Myelon SHM) ──"
    run_cell "ctx${ctx}_myelon_typed_kv" "myelon://default" "$PROMPTS" \
        --force-runner --myelon-ipc --myelon-access-mode typed || echo "  myelon_typed_kv cell failed"
    typed_kv_pct=$(read_success_pct "ctx${ctx}_myelon_typed_kv")
    echo "  → myelon_typed_kv success: ${typed_kv_pct}%"
    echo ""

    # Per-bucket gate for skipping larger contexts
    if [[ $typed_kv_pct -lt $MIN_SUCCESS_FOR_NEXT_BUCKET && "$FORCE_ALL_CELLS" != "1" ]]; then
        echo "  ⚠️  myelon_typed_kv at ctx=${ctx} got ${typed_kv_pct}% < ${MIN_SUCCESS_FOR_NEXT_BUCKET}% — past envelope."
        echo "  ⚠️  Skipping all larger buckets ($(echo "$CTX_BUCKETS" | tr ' ' '\n' | awk -v c=$ctx 'NR>0 && $1>c {print}' | tr '\n' ' '))"
        skip_remaining_buckets=1
    fi
done

# Aggregator: handle stubs (skipped/aborted cells) gracefully.
echo "═══ aggregate ═══"
python3 - <<PYEOF
import json, glob, os
out_dir = "$OUT_DIR"
def stat(d, *path):
    cur = d
    for p in path:
        if cur is None: return None
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur
print(f"{'cell':<32} {'rps':>7} {'ok%':>5} {'ttft50':>9} {'ttft99':>9} {'note':>14}")
print("-" * 80)
for path in sorted(glob.glob(os.path.join(out_dir, "*_results.json"))):
    bn = os.path.basename(path).replace("_results.json","")
    d = json.load(open(path))
    a = d.get('aggregate', {})
    note = ""
    if d.get("skipped_due_to_socket_failure"):  note = "SKIP (socket)"
    if d.get("aborted_by_smoke_probe"):         note = "SKIP (smoke)"
    rps = stat(a,'req_per_s','median')
    sr  = stat(a,'success_rate','median')
    ttft50 = stat(a,'ttft_ms','p50','median')
    ttft99 = stat(a,'ttft_ms','p99','median')
    f = lambda v: f"{v:>7.3f}" if v is not None else "      —"
    fi = lambda v: f"{v:>9.0f}" if v is not None else "        —"
    pc = lambda v: f"{v*100:>4.0f}%" if v is not None else "    —"
    print(f"{bn:<32} {f(rps)} {pc(sr)} {fi(ttft50)} {fi(ttft99)} {note:>14}")
PYEOF
