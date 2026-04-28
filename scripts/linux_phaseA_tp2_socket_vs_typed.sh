#!/usr/bin/env bash
# RFC 0038 Phase A: single-engine TP=2 socket vs myelon_typed sanity.
# Reproduces prior 4× H200 phase 8.8: must show +1-3% rps on myelon_typed.
#
# Usage:
#   MODEL=Qwen/Qwen3-30B-A3B  CTX=1024  CONC=8  NUM_REQS=200 \
#   PROMPTS_FILE=.../sharegpt_1k.jsonl  OUT_DIR=.../phaseA_smoke_30B_tp2_c8 \
#   SOCKET_BIN=.../socket-h200/vllm-rs  MYELON_BIN=.../myelon-rkyv-h200/vllm-rs \
#   ./linux_phaseA_tp2_socket_vs_typed.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

: "${MODEL:?MODEL required}"
: "${CTX:?CTX required}"
: "${CONC:?CONC required}"
: "${NUM_REQS:?NUM_REQS required}"
: "${PROMPTS_FILE:?PROMPTS_FILE required}"
: "${OUT_DIR:?OUT_DIR required}"
: "${SOCKET_BIN:?SOCKET_BIN required}"
: "${MYELON_BIN:?MYELON_BIN required}"

PROMPT_MIN_TOK=${PROMPT_MIN_TOK:-$(( CTX - 256 ))}
PROMPT_MAX_TOK=${PROMPT_MAX_TOK:-$(( CTX + 1024 ))}
MAX_TOKENS=${MAX_TOKENS:-64}
WARMUP_RUNS=${WARMUP_RUNS:-1}
REPEAT_RUNS=${REPEAT_RUNS:-1}

mkdir -p "$OUT_DIR"

PORT=18000
PYTHON=${PYTHON:-/root/Documents/myelon-launch/vllm/.venv/bin/python}

cleanup() {
    pkill -f "vllm-rs --server" 2>/dev/null || true
    sleep 2
    pkill -9 -f "vllm-rs --server" 2>/dev/null || true
    rm -f /dev/shm/myelon_* 2>/dev/null || true
    sleep 1
}
trap cleanup EXIT INT TERM

run_mode() {
    local label="$1"
    local bin="$2"
    shift 2
    local extra=("$@")

    echo "── $label ──"
    cleanup

    "$bin" --server --port $PORT --m "$MODEL" --num-shards 2 --device-ids 0,1 \
        --max-model-len $CTX --force-runner \
        "${extra[@]}" > "$OUT_DIR/${label}_server.log" 2>&1 &
    local SRV_PID=$!

    for i in $(seq 1 ${BOOT_TIMEOUT_S:-240}); do
        if curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
            echo "  [$label] up after ${i}s"
            break
        fi
        if ! kill -0 $SRV_PID 2>/dev/null; then
            echo "  [$label] ❌ server died during boot"
            return 1
        fi
        sleep 1
    done
    if ! curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
        echo "  [$label] ❌ did not come up"
        kill $SRV_PID 2>/dev/null
        return 1
    fi

    "$PYTHON" "$SCRIPT_DIR/bench_stress_sharegpt.py" \
        --url "http://127.0.0.1:$PORT" \
        --served-model-name qwen3 \
        --prompts-file "$PROMPTS_FILE" \
        --prompt-min-tok $PROMPT_MIN_TOK --prompt-max-tok $PROMPT_MAX_TOK \
        --max-tokens $MAX_TOKENS \
        --concurrency $CONC \
        --num-requests $NUM_REQS \
        --warmup-runs $WARMUP_RUNS --repeat-runs $REPEAT_RUNS \
        --no-stream \
        --output-file "$OUT_DIR/${label}_results.json" \
        > "$OUT_DIR/${label}_bench.log" 2>&1 || echo "  [$label] ❌ bench failed"

    if [ -f "$OUT_DIR/${label}_results.json" ]; then
        "$PYTHON" -c "
import json
d = json.load(open('$OUT_DIR/${label}_results.json'))
ag = d['aggregate']
rps = ag['req_per_s']['median']
ttft = ag['ttft_ms']['p50']['median']
e2e = ag['latency_ms']['p50']['median']
print(f'  [$label] rps={rps:.3f} ttft_p50={ttft:.1f}ms e2e_p50={e2e:.1f}ms')
"
    fi
    cleanup
}

echo "================================================================"
echo "RFC 0038 Phase A: TP=2 socket vs myelon_typed sanity"
echo "MODEL=$MODEL CTX=$CTX CONC=$CONC NUM_REQS=$NUM_REQS"
echo "================================================================"
echo

run_mode "socket" "$SOCKET_BIN"
run_mode "myelon_typed" "$MYELON_BIN" --myelon-ipc

echo
echo "── Δ ──"
"$PYTHON" - <<EOF
import json, os
out = "$OUT_DIR"
modes = ["socket", "myelon_typed"]
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
print(f"{'mode':>14} | {'rps':>7} | {'Δ vs socket':>12} | {'TTFT p50':>10} | {'E2E p50':>10}")
print("-" * 70)
base = rows["socket"]["rps"] if rows.get("socket") else None
for m in modes:
    r = rows[m]
    if r is None:
        print(f"{m:>14} | (missing)")
        continue
    ds = f"{(r['rps']/base - 1)*100:+.2f}%" if base else "—"
    print(f"{m:>14} | {r['rps']:>7.3f} | {ds:>12} | {r['ttft']:>8.1f}ms | {r['e2e']:>8.1f}ms")
EOF
