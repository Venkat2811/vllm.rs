#!/usr/bin/env bash
# RFC 0038 Phase B harness: run all 4 transport modes for one PD-tp1-tp1 cell.
#
# Modes:
#   socket           : socket-h200 binary, --pd-url tcp://127.0.0.1:$PD_PORT
#   myelon_typed     : myelon-rkyv-h200 binary, +myelon-ipc, KV over TCP
#   myelon_typed_kv  : myelon-rkyv-h200 binary, +myelon-ipc, KV over Myelon SHM
#   cuda_ipc         : socket-h200 binary, --pd-url file:///tmp/sock_pd  (CUDA-IPC)
#
# Server: GPU 0 (--pd-server). Client: GPU 1 (--pd-client). KV transferred
# through the chosen transport between them.
#
# Usage:
#   MODEL=Qwen/Qwen3-30B-A3B CTX=4096 CONC=4 NUM_REQS=80 \
#   PROMPTS_FILE=.../sharegpt_4k.jsonl  OUT_DIR=.../phaseB_pd_tp1_30B_ctx4k_c4 \
#   SOCKET_BIN=.../binaries/socket-h200/vllm-rs \
#   MYELON_BIN=.../binaries/myelon-rkyv-h200/vllm-rs \
#   ./linux_pd_tp1_4mode_bench.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

: "${MODEL:?MODEL required (e.g. Qwen/Qwen3-30B-A3B)}"
: "${CTX:?CTX required (max-model-len for the cell)}"
: "${CONC:?CONC required (closed-loop concurrency)}"
: "${NUM_REQS:?NUM_REQS required}"
: "${PROMPTS_FILE:?PROMPTS_FILE required (pre-bucketed jsonl)}"
: "${OUT_DIR:?OUT_DIR required}"
: "${SOCKET_BIN:?SOCKET_BIN required}"
: "${EXTRA_BIN_ARGS:=}"
: "${MYELON_BIN:?MYELON_BIN required}"

PROMPT_MIN_TOK=${PROMPT_MIN_TOK:-$(( CTX - 256 ))}
PROMPT_MAX_TOK=${PROMPT_MAX_TOK:-$(( CTX + 1024 ))}
MAX_TOKENS=${MAX_TOKENS:-64}
WARMUP_RUNS=${WARMUP_RUNS:-1}
REPEAT_RUNS=${REPEAT_RUNS:-1}

mkdir -p "$OUT_DIR"

# Find free ports (pre-claim 3 per mode; release before each)
HTTP_S=18000
PD_PORT=18001
HTTP_C=18002

PYTHON=${PYTHON:-/root/Documents/myelon-launch/vllm/.venv/bin/python}

cleanup() {
    pkill -f "vllm-rs --pd-" 2>/dev/null || true
    sleep 2
    pkill -9 -f "vllm-rs --pd-" 2>/dev/null || true
    # Linux SHM cleanup
    rm -f /dev/shm/myelon_* /tmp/sock_pd 2>/dev/null || true
    sleep 1
}
trap cleanup EXIT INT TERM

run_mode() {
    local label="$1"
    local bin="$2"
    local pd_url="$3"
    shift 3
    local extra=("$@")

    echo "── $label ── bin=$(basename $(dirname $bin))  pd_url=$pd_url"
    cleanup

    "$bin" --pd-server --port $HTTP_S --m "$MODEL" --d 0 \
        --max-model-len $CTX --pd-url "$pd_url" --force-runner $EXTRA_BIN_ARGS \
        "${extra[@]}" > "$OUT_DIR/${label}_server.log" 2>&1 &
    local SRV_PID=$!

    "$bin" --server --pd-client --port $HTTP_C --m "$MODEL" --d 1 \
        --max-model-len $CTX --pd-url "$pd_url" --force-runner $EXTRA_BIN_ARGS \
        "${extra[@]}" > "$OUT_DIR/${label}_client.log" 2>&1 &
    local CLI_PID=$!

    # Wait up to 240s for client API to be ready
    for i in $(seq 1 240); do
        if curl -sf "http://127.0.0.1:$HTTP_C/v1/models" >/dev/null 2>&1; then
            echo "  [$label] client up after ${i}s"
            break
        fi
        if ! kill -0 $SRV_PID 2>/dev/null; then
            echo "  [$label] ❌ server died during boot"
            kill $CLI_PID 2>/dev/null || true
            return 1
        fi
        if ! kill -0 $CLI_PID 2>/dev/null; then
            echo "  [$label] ❌ client died during boot"
            kill $SRV_PID 2>/dev/null || true
            return 1
        fi
        sleep 1
    done
    if ! curl -sf "http://127.0.0.1:$HTTP_C/v1/models" >/dev/null 2>&1; then
        echo "  [$label] ❌ client did not come up in 240s"
        kill $SRV_PID $CLI_PID 2>/dev/null || true
        return 1
    fi

    # Run the bench
    "$PYTHON" "$SCRIPT_DIR/bench_stress_sharegpt.py" \
        --url "http://127.0.0.1:$HTTP_C" \
        --served-model-name qwen3 \
        --prompts-file "$PROMPTS_FILE" \
        --prompt-min-tok $PROMPT_MIN_TOK --prompt-max-tok $PROMPT_MAX_TOK \
        --max-tokens $MAX_TOKENS \
        --concurrency $CONC \
        --num-requests $NUM_REQS \
        --warmup-runs $WARMUP_RUNS --repeat-runs $REPEAT_RUNS \
        --no-stream \
        --output-file "$OUT_DIR/${label}_results.json" \
        > "$OUT_DIR/${label}_bench.log" 2>&1 || {
            echo "  [$label] ❌ bench failed (see ${label}_bench.log)"
        }

    # Tail summary
    if [ -f "$OUT_DIR/${label}_results.json" ]; then
        "$PYTHON" -c "
import json
d = json.load(open('$OUT_DIR/${label}_results.json'))
ag = d['aggregate']
rps = ag['req_per_s']['median']
ttft = ag['ttft_ms']['p50']['median']
e2e = ag['latency_ms']['p50']['median']
print(f'  [$label] rps={rps:.3f} ttft_p50={ttft:.1f}ms e2e_p50={e2e:.1f}ms')
" 2>/dev/null || echo "  [$label] (parse error)"
    fi

    cleanup
}

echo "================================================================"
echo "RFC 0038 Phase B cell: $(basename $OUT_DIR)"
echo "MODEL=$MODEL CTX=$CTX CONC=$CONC NUM_REQS=$NUM_REQS"
echo "PROMPT_TOK_RANGE=[$PROMPT_MIN_TOK, $PROMPT_MAX_TOK)"
echo "OUT_DIR=$OUT_DIR"
echo "================================================================"
echo

# Mode 1: socket baseline
run_mode "socket" "$SOCKET_BIN" "tcp://127.0.0.1:$PD_PORT"

# Mode 2: myelon engine↔runner, KV over TCP loopback
run_mode "myelon_typed" "$MYELON_BIN" "tcp://127.0.0.1:$PD_PORT" --myelon-ipc

# Mode 3: full myelon stack — engine↔runner + KV over Myelon SHM
run_mode "myelon_typed_kv" "$MYELON_BIN" "myelon://default" --myelon-ipc

# Mode 4: CUDA-IPC baseline (the production fast path Myelon must beat)
run_mode "cuda_ipc" "$SOCKET_BIN" "file:///tmp/sock_pd"

echo
echo "── Δ rollup (rps) ──"
"$PYTHON" - <<EOF
import json, os
out = "$OUT_DIR"
modes = ["socket", "myelon_typed", "myelon_typed_kv", "cuda_ipc"]
rows = {}
for m in modes:
    p = os.path.join(out, f"{m}_results.json")
    if not os.path.exists(p):
        rows[m] = None
        continue
    d = json.load(open(p))
    ag = d["aggregate"]
    rows[m] = {
        "rps":   ag["req_per_s"]["median"],
        "ttft":  ag["ttft_ms"]["p50"]["median"],
        "e2e":   ag["latency_ms"]["p50"]["median"],
    }

print(f"{'mode':>18} | {'rps':>7} | {'Δ vs socket':>13} | {'Δ vs cuda_ipc':>14} | {'TTFT p50':>10} | {'E2E p50':>10}")
print("-" * 95)
base_s = rows["socket"]["rps"] if rows.get("socket") else None
base_c = rows["cuda_ipc"]["rps"] if rows.get("cuda_ipc") else None
for m in modes:
    r = rows[m]
    if r is None:
        print(f"{m:>18} | (missing)")
        continue
    ds = f"{(r['rps']/base_s - 1)*100:+.1f}%" if base_s else "—"
    dc = f"{(r['rps']/base_c - 1)*100:+.1f}%" if base_c else "—"
    print(f"{m:>18} | {r['rps']:>7.2f} | {ds:>13} | {dc:>14} | {r['ttft']:>8.1f}ms | {r['e2e']:>8.1f}ms")
EOF

echo "Done. Cell artifacts: $OUT_DIR"
