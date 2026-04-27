#!/usr/bin/env bash
# RFC 0034 P2.5 — scaling sweep on Mac M3 Max.
# Tests whether the typed-mode decode delta scales with batch + max_tokens.
#
# Hypothesis: typed mode skips ~(batch × steps) heap alloc/free pairs.
# So the delta should grow with batch and with max_tokens.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

BIN=./target/release/vllm-rs
MODEL=Qwen/Qwen3-0.6B
MAXLEN=4096

OUT_DIR="$ROOT/scripts/mac_p2_5_scaling_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Artifacts: $OUT_DIR"
echo ""

CONFIGS=(
    "8:64"      # batch=8, max_tokens=64    (the current bench)
    "8:256"     # batch=8, more decode steps
    "32:64"     # bigger batch, short decode
    "32:256"    # bigger batch, more decode
    "64:128"    # large batch
    "128:128"   # max batch on M3 Max
)

run_cell() {
    local label="$1" mode="$2" batch="$3" maxtok="$4"; shift 4
    local args=("$@")
    local log="$OUT_DIR/${label}_b${batch}_m${maxtok}_${mode}.log"
    "$BIN" --m "$MODEL" --d 0 \
        --batch $batch --max-tokens $maxtok --max-model-len $MAXLEN \
        --prompts "Tell me about distributed systems and shared memory in detail." \
        "${args[@]}" 2>&1 > "$log"
    grep -E "Prompt tokens|Decoded tokens" "$log" | head -2
}

for cfg in "${CONFIGS[@]}"; do
    IFS=: read -r BATCH MAXTOK <<< "$cfg"
    echo "═══ batch=$BATCH max_tokens=$MAXTOK ═══"
    for run in 1 2; do
        echo "  run $run / 2:"
        echo "    socket:"
        run_cell "run${run}" "socket" $BATCH $MAXTOK --force-runner | sed 's/^/      /'
        echo "    typed:"
        run_cell "run${run}" "typed"  $BATCH $MAXTOK --force-runner --myelon-ipc --myelon-access-mode typed | sed 's/^/      /'
    done
    echo ""
done

echo "═══ Aggregate ═══"
python3 - <<EOF
import re, glob, os, statistics

out_dir = "$OUT_DIR"
data = {}  # (batch, maxtok, mode) -> {prompt: [], decode: []}

for path in sorted(glob.glob(os.path.join(out_dir, "*.log"))):
    name = os.path.basename(path).replace(".log","")
    m = re.match(r"run\d+_b(\d+)_m(\d+)_(socket|typed)", name)
    if not m: continue
    batch, maxtok, mode = int(m.group(1)), int(m.group(2)), m.group(3)
    text = open(path).read()
    pm = re.search(r"Prompt tokens:.*?\(([\d.]+) tokens/s\)", text)
    dm = re.search(r"Decoded tokens:.*?\(([\d.]+) tokens/s\)", text)
    key = (batch, maxtok, mode)
    data.setdefault(key, {"prompt": [], "decode": []})
    if pm: data[key]["prompt"].append(float(pm.group(1)))
    if dm: data[key]["decode"].append(float(dm.group(1)))

print()
print(f"{'batch':>5} {'maxtok':>6} {'sock_prompt':>11} {'typ_prompt':>11} {'Δp%':>6} | {'sock_decode':>11} {'typ_decode':>11} {'Δd%':>6}")
print("-" * 90)
keys = sorted({(b, t) for b, t, _ in data.keys()})
for b, t in keys:
    sk = data.get((b, t, "socket"), {"prompt":[0],"decode":[0]})
    ty = data.get((b, t, "typed"),  {"prompt":[0],"decode":[0]})
    sp = statistics.median(sk["prompt"]) if sk["prompt"] else 0
    sd = statistics.median(sk["decode"]) if sk["decode"] else 0
    tp = statistics.median(ty["prompt"]) if ty["prompt"] else 0
    td = statistics.median(ty["decode"]) if ty["decode"] else 0
    dp = (tp-sp)/sp*100 if sp else 0
    dd = (td-sd)/sd*100 if sd else 0
    print(f"{b:>5} {t:>6} {sp:>11.0f} {tp:>11.0f} {dp:>+5.1f}% | {sd:>11.0f} {td:>11.0f} {dd:>+5.1f}%")
EOF
