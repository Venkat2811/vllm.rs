#!/usr/bin/env bash
# Mac M3 Max PD-mode multi-turn bench: socket vs Myelon-typed (KV=tcp) vs
# Myelon-typed (KV=Myelon SHM) across rounds-per-session sweep.
#
# Hypothesis (RFC 0037): with prefix caching enabled, multi-turn workloads
# accumulate shared prefixes across rounds, and the cache hit rate climbs.
# Test whether Myelon-KV transport changes anything for multi-turn (likely
# negligible — the KV transfer per turn is bounded by the per-turn delta,
# not the cumulative context). The headline metric is cache_hit_rate per
# round, validated via the new prompt_tokens_details.cached_tokens field.
#
# Methodology:
#   - bench_stress_multiturn.py drives N concurrent sessions, each with R
#     rounds. First turn uses 200-500 tok prompts; follow-ups use truncated
#     fresh prompts (--turn-input-tokens) to bound per-round growth.
#   - Each cell runs all R rounds for all sessions, then we compute per-round
#     cache hit rate from usage.prompt_tokens_details.cached_tokens.
#   - --force-runner symmetry between socket and Myelon paths.
#   - Cleanup between cells via lib/cleanup_mac_bench.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/cleanup_mac_bench.sh"

BIN=./target/release/vllm-rs
MODEL=${MODEL:-Qwen/Qwen3-4B}
NUM_CLIENTS=${NUM_CLIENTS:-4}
NUM_SESSIONS=${NUM_SESSIONS:-20}
ROUNDS_LIST=${ROUNDS_LIST:-"1 5 10 20"}
TURN_INPUT_TOKENS=${TURN_INPUT_TOKENS:-300}
TURN_OUTPUT_TOKENS=${TURN_OUTPUT_TOKENS:-64}
MAXLEN=${MAXLEN:-16384}
PROMPTS=${PROMPTS:-$ROOT/scripts/long_ctx_buckets/multiturn_first_turn.jsonl}

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

OUT_DIR="$ROOT/scripts/mac_pd_multiturn_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Model: $MODEL  clients: $NUM_CLIENTS  sessions/cell: $NUM_SESSIONS"
echo "Rounds sweep: $ROUNDS_LIST  turn_in_tok: $TURN_INPUT_TOKENS  turn_out_tok: $TURN_OUTPUT_TOKENS"
echo "Max model len: $MAXLEN"
echo "Prompts: $PROMPTS"
echo "Ports: srv=$HTTP_S pd=$PD_PORT cli=$HTTP_C"
echo "Artifacts: $OUT_DIR"
echo ""

if [[ ! -f "$PROMPTS" ]]; then
    echo "❌ missing $PROMPTS — run build_multiturn_first_turn.py first"
    exit 1
fi

run_cell() {
    local label="$1" pd_url="$2" rounds="$3"; shift 3
    local extra=("$@")
    cleanup_between_cells "$HTTP_C"

    local mns=$((NUM_CLIENTS * 2))
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

    uv run --with aiohttp python3 \
        "$SCRIPT_DIR/bench_stress_multiturn.py" \
        --url "http://127.0.0.1:$HTTP_C" \
        --served-model-name qwen3 \
        --prompts-file "$PROMPTS" \
        --num-clients $NUM_CLIENTS \
        --num-sessions $NUM_SESSIONS \
        --rounds $rounds \
        --turn-input-tokens $TURN_INPUT_TOKENS \
        --turn-output-tokens $TURN_OUTPUT_TOKENS \
        --output-file "$OUT_DIR/${label}_results.json" \
        > "$OUT_DIR/${label}_bench.log" 2>&1
    local rc=$?

    kill $SERVER_PID $CLIENT_PID 2>/dev/null
    sleep 2
    cleanup_between_cells "$HTTP_C"
    return $rc
}

for r in $ROUNDS_LIST; do
    echo "═══ rounds=${r} ═══"

    echo "── pd_socket (KV=tcp) ──"
    run_cell "r${r}_socket" "tcp://127.0.0.1:$PD_PORT" "$r" --force-runner || echo "  cell failed"
    echo ""

    echo "── pd_myelon_typed (KV=tcp) ──"
    run_cell "r${r}_myelon_typed" "tcp://127.0.0.1:$PD_PORT" "$r" \
        --force-runner --myelon-ipc --myelon-access-mode typed || echo "  cell failed"
    echo ""

    echo "── pd_myelon_typed_kv (KV=Myelon SHM) ──"
    run_cell "r${r}_myelon_typed_kv" "myelon://default" "$r" \
        --force-runner --myelon-ipc --myelon-access-mode typed || echo "  cell failed"
    echo ""
done

echo "═══ aggregate ═══"
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

print(f"{'cell':<32} {'turns/s':>9} {'ok%':>6} {'elapsed':>9} {'hit%':>7}")
print("-" * 70)
for name in sorted(data.keys()):
    d = data[name]
    tps = f"{d['turns_per_s']:>9.3f}" if d['turns_per_s'] is not None else "        —"
    ok  = f"{d['success_rate']*100:>5.0f}%" if d['success_rate'] is not None else "    —"
    el  = f"{d['elapsed_s']:>8.1f}s" if d['elapsed_s'] is not None else "        —"
    hr  = f"{d['overall_hit']*100:>6.1f}%" if d['overall_hit'] is not None else "      —"
    print(f"{name:<32} {tps} {ok} {el} {hr}")

print()
print("Per-round hit rate (mean), by cell:")
all_rounds = sorted({r['round'] for d in data.values() for r in d.get('per_round') or []})
header = "  " + "cell".ljust(32) + "".join(f" r{r:>2}      " for r in all_rounds)
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
    print("  " + name.ljust(32) + "".join(cells))
EOF
