#!/usr/bin/env bash
# Mac M3 Max multi-turn campaign harness — runs both Matrix S (single-process)
# and Matrix P (PD-tp1-tp1) in sequence on the same model.
#
# Matrix S — engine↔runner Myelon-IPC axis (no PD)
#   modes: socket runner / Myelon-typed runner
#   rounds: ROUND_LIST (default 1, 5, 10, 20)
#
# Matrix P — KV-transport axis (PD-tp1-tp1, prefix cache enabled)
#   modes: socket / Myelon-typed-KVtcp / Myelon-typed-KVmyelon
#   rounds: ROUND_LIST
#
# Each cell = bench_stress_multiturn.py with N sessions, concurrency 4.
# Per-cell servers come up fresh and tear down between cells.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/cleanup_mac_bench.sh"

BIN=./target/release/vllm-rs
MODEL=${MODEL:-Qwen/Qwen3-8B}
NUM_CLIENTS=${NUM_CLIENTS:-4}
NUM_SESSIONS=${NUM_SESSIONS:-16}
ROUND_LIST=${ROUND_LIST:-"1 5 10 20"}
TURN_INPUT_TOKENS=${TURN_INPUT_TOKENS:-200}
TURN_OUTPUT_TOKENS=${TURN_OUTPUT_TOKENS:-64}
MAXLEN=${MAXLEN:-8192}
PROMPTS=${PROMPTS:-$ROOT/scripts/long_ctx_buckets/multiturn_first_turn.jsonl}

# Skip flags
SKIP_S=${SKIP_S:-0}
SKIP_P=${SKIP_P:-0}

# Find free ports
for p in 18000 19000 20000 21000 22000 23000; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { HTTP_S=$p; break; }
done
for p in 18001 19001 20001 21001 22001 23001; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { PD_PORT=$p; break; }
done
for p in 18002 19002 20002 21002 22002 23002; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { HTTP_C=$p; break; }
done

OUT_DIR="$ROOT/scripts/mac_multiturn_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Model: $MODEL  clients: $NUM_CLIENTS  sessions/cell: $NUM_SESSIONS"
echo "Rounds: $ROUND_LIST  turn_in: $TURN_INPUT_TOKENS  turn_out: $TURN_OUTPUT_TOKENS  maxlen: $MAXLEN"
echo "Prompts: $PROMPTS"
echo "Ports: srv=$HTTP_S pd=$PD_PORT cli=$HTTP_C"
echo "Artifacts: $OUT_DIR"
echo "SKIP_S=$SKIP_S SKIP_P=$SKIP_P"
echo ""

if [[ ! -f "$PROMPTS" ]]; then
    echo "❌ missing $PROMPTS — run build_multiturn_first_turn.py first"
    exit 1
fi

run_bench() {
    local label="$1" rounds="$2" url="$3"
    uv run --with aiohttp python3 \
        "$SCRIPT_DIR/bench_stress_multiturn.py" \
        --url "$url" \
        --served-model-name qwen3 \
        --prompts-file "$PROMPTS" \
        --num-clients "$NUM_CLIENTS" \
        --num-sessions "$NUM_SESSIONS" \
        --rounds "$rounds" \
        --turn-input-tokens "$TURN_INPUT_TOKENS" \
        --turn-output-tokens "$TURN_OUTPUT_TOKENS" \
        --output-file "$OUT_DIR/${label}_results.json" \
        > "$OUT_DIR/${label}_bench.log" 2>&1
    return $?
}

# ===========================================================================
# Matrix S — single-process (engine↔runner Myelon-IPC axis)
# ===========================================================================
if [[ "$SKIP_S" != "1" ]]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "  MATRIX S — single-process (engine↔runner)"
    echo "═══════════════════════════════════════════════════════════════"

    run_s_cell() {
        local label="$1" rounds="$2"; shift 2
        local extra=("$@")
        cleanup_between_cells "$HTTP_S"

        "$BIN" --m "$MODEL" --d 0 --server --port $HTTP_S \
            --max-model-len "$MAXLEN" --max-num-seqs 16 --force-runner --prefix-cache \
            "${extra[@]}" > "$OUT_DIR/${label}_server.log" 2>&1 &
        SERVER_PID=$!

        for i in $(seq 1 180); do
            curl -sf http://127.0.0.1:$HTTP_S/v1/models >/dev/null 2>&1 && break
            sleep 1
        done
        if ! curl -sf http://127.0.0.1:$HTTP_S/v1/models >/dev/null 2>&1; then
            echo "  ❌ ${label} server did not come up"
            kill $SERVER_PID 2>/dev/null
            return 1
        fi

        run_bench "$label" "$rounds" "http://127.0.0.1:$HTTP_S"
        local rc=$?
        kill $SERVER_PID 2>/dev/null
        sleep 2
        cleanup_between_cells "$HTTP_S"
        return $rc
    }

    for r in $ROUND_LIST; do
        echo "── S r=$r socket ──"
        run_s_cell "S_socket_r${r}" "$r" || echo "  S socket r=$r failed"
        echo ""
        echo "── S r=$r myelon-typed ──"
        run_s_cell "S_myelon_r${r}" "$r" --myelon-ipc --myelon-access-mode typed || echo "  S myelon r=$r failed"
        echo ""
    done
fi

# ===========================================================================
# Matrix P — PD-tp1-tp1 (KV-transport axis)
# ===========================================================================
if [[ "$SKIP_P" != "1" ]]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "  MATRIX P — PD-tp1-tp1 (KV transport)"
    echo "═══════════════════════════════════════════════════════════════"

    run_p_cell() {
        local label="$1" rounds="$2" pd_url="$3"; shift 3
        local extra=("$@")
        cleanup_between_cells "$HTTP_C"

        "$BIN" --pd-server --port $HTTP_S --m "$MODEL" --d 0 \
            --max-model-len "$MAXLEN" --max-num-seqs 8 --pd-url "$pd_url" --prefix-cache \
            "${extra[@]}" > "$OUT_DIR/${label}_pdserver.log" 2>&1 &
        SERVER_PID=$!

        "$BIN" --server --pd-client --port $HTTP_C --m "$MODEL" --d 0 \
            --max-model-len "$MAXLEN" --max-num-seqs 8 --pd-url "$pd_url" --prefix-cache \
            "${extra[@]}" > "$OUT_DIR/${label}_pdclient.log" 2>&1 &
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

        run_bench "$label" "$rounds" "http://127.0.0.1:$HTTP_C"
        local rc=$?
        kill $SERVER_PID $CLIENT_PID 2>/dev/null
        sleep 2
        cleanup_between_cells "$HTTP_C"
        return $rc
    }

    for r in $ROUND_LIST; do
        echo "── P r=$r pd_socket (KV=tcp) ──"
        run_p_cell "P_socket_r${r}" "$r" "tcp://127.0.0.1:$PD_PORT" --force-runner || echo "  P socket r=$r failed"
        echo ""
        echo "── P r=$r pd_myelon_typed (KV=tcp) ──"
        run_p_cell "P_myelon_typed_r${r}" "$r" "tcp://127.0.0.1:$PD_PORT" \
            --force-runner --myelon-ipc --myelon-access-mode typed || echo "  P myelon-typed r=$r failed"
        echo ""
        echo "── P r=$r pd_myelon_typed_kv (KV=Myelon SHM) ──"
        run_p_cell "P_myelon_typed_kv_r${r}" "$r" "myelon://default" \
            --force-runner --myelon-ipc --myelon-access-mode typed || echo "  P myelon-typed-kv r=$r failed"
        echo ""
    done
fi

# ===========================================================================
# Aggregate
# ===========================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "  AGGREGATE"
echo "═══════════════════════════════════════════════════════════════"
python3 - <<EOF
import json, glob, os
out_dir = "$OUT_DIR"
data = {}
for path in sorted(glob.glob(os.path.join(out_dir, "*_results.json"))):
    with open(path) as f:
        d = json.load(f)
    name = os.path.basename(path).replace("_results.json","")
    agg = d.get("aggregate", {})
    overall = agg.get("overall", {})
    per_round = agg.get("per_round", [])
    data[name] = {
        "turns_per_s": overall.get("turns_per_s"),
        "success_rate": overall.get("success_rate"),
        "elapsed_s": overall.get("elapsed_s"),
        "overall_hit": overall.get("overall_cache_hit_rate"),
        "per_round": per_round,
    }

print(f"{'cell':<35} {'turns/s':>9} {'ok%':>6} {'elapsed':>10} {'hit%':>7}")
print("-" * 75)
for name in sorted(data.keys()):
    d = data[name]
    tps = f"{d['turns_per_s']:>9.3f}" if d['turns_per_s'] is not None else "        —"
    ok  = f"{d['success_rate']*100:>5.0f}%" if d['success_rate'] is not None else "    —"
    el  = f"{d['elapsed_s']:>9.1f}s" if d['elapsed_s'] is not None else "        —"
    hr  = f"{d['overall_hit']*100:>6.1f}%" if d['overall_hit'] is not None else "      —"
    print(f"{name:<35} {tps} {ok} {el} {hr}")

print()
all_rounds = sorted({r['round'] for d in data.values() for r in d.get('per_round') or []})
if all_rounds:
    print("Per-round mean cache hit rate (matters most for round 2+):")
    header = "  " + "cell".ljust(35) + "".join(f" r{r:>2}     " for r in all_rounds)
    print(header)
    for name in sorted(data.keys()):
        by_round = {r['round']: r for r in data[name].get('per_round') or []}
        cells = []
        for r in all_rounds:
            rec = by_round.get(r)
            if rec:
                hit = rec['cache_hit_rate']['mean'] * 100
                cells.append(f" {hit:>6.1f}%")
            else:
                cells.append("       —")
        print("  " + name.ljust(35) + "".join(cells))
EOF

echo ""
echo "DONE — artifacts at $OUT_DIR"
