#!/usr/bin/env bash
# Sanity rerun: shuffled mode order across 3 runs to rule out warmup contamination.
# Run 1: typed → owned → socket
# Run 2: owned → socket → typed
# Run 3: socket → typed → owned
#
# If the +76% decode_tps delta in mac_p2_4_ab.sh is warmup, shuffling will
# scramble it. If it's real, the delta will hold.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

BIN=./target/release/vllm-rs
MODEL=Qwen/Qwen3-0.6B
BATCH=8
MAXTOK=64
MAXLEN=2048

OUT_DIR="$ROOT/scripts/mac_p2_4_ab_shuffled_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Artifacts: $OUT_DIR"
echo ""

run_one() {
    local label="$1" mode_label="$2"; shift; shift
    local args=("$@")
    local log="$OUT_DIR/${label}_${mode_label}.log"
    "$BIN" --m "$MODEL" --d 0 \
        --batch $BATCH --max-tokens $MAXTOK --max-model-len $MAXLEN \
        --prompts "Tell me about distributed systems and shared memory." \
        "${args[@]}" 2>&1 > "$log"
    grep -E "Prompt tokens|Decoded tokens" "$log" | head -2
    echo ""
}

ORDERS=(
    "typed:owned:socket"
    "owned:socket:typed"
    "socket:typed:owned"
)

for i in 0 1 2; do
    run=$((i + 1))
    IFS=: read -r m1 m2 m3 <<< "${ORDERS[$i]}"
    echo "═══ Run $run / 3   order: $m1 → $m2 → $m3 ═══"
    for m in "$m1" "$m2" "$m3"; do
        case $m in
          socket) run_one "run${run}" "socket"  --force-runner ;;
          owned)  run_one "run${run}" "owned"   --force-runner --myelon-ipc --myelon-access-mode owned ;;
          typed)  run_one "run${run}" "typed"   --force-runner --myelon-ipc --myelon-access-mode typed ;;
        esac
    done
done

echo "═══ Aggregate (median across runs, regardless of order) ═══"
python3 - <<EOF
import re, glob, os, statistics

out_dir = "$OUT_DIR"
modes = ["socket", "owned", "typed"]
data = {m: {"prompt_tps": [], "decode_tps": []} for m in modes}

for path in sorted(glob.glob(os.path.join(out_dir, "*.log"))):
    name = os.path.basename(path).replace(".log","")
    parts = name.split("_")
    mode = parts[-1]
    if mode not in modes: continue
    text = open(path).read()
    m_p = re.search(r"Prompt tokens:.*?\(([\d.]+) tokens/s\)", text)
    m_d = re.search(r"Decoded tokens:.*?\(([\d.]+) tokens/s\)", text)
    if m_p: data[mode]["prompt_tps"].append(float(m_p.group(1)))
    if m_d: data[mode]["decode_tps"].append(float(m_d.group(1)))

print()
print(f"{'mode':<8} {'prompt_tps median':>20} {'decode_tps median':>20}")
print("-" * 52)
medians = {}
for m in modes:
    p = data[m]["prompt_tps"]; d = data[m]["decode_tps"]
    pm = statistics.median(p) if p else 0
    dm = statistics.median(d) if d else 0
    medians[m] = (pm, dm)
    print(f"{m:<8} {pm:>20.2f} {dm:>20.2f}")
print()
sk = medians["socket"]
print("Δ vs socket (median over 3 shuffled runs):")
for m in ["owned", "typed"]:
    cm = medians[m]
    if sk[0] > 0:
        dp = (cm[0]-sk[0])/sk[0]*100
        dd = (cm[1]-sk[1])/sk[1]*100
        print(f"  {m:<6}: ΔPROMPT={dp:+6.2f}%  ΔDECODE={dd:+6.2f}%")

print()
ow = medians["owned"]; ty = medians["typed"]
if ow[0] > 0:
    dp = (ty[0]-ow[0])/ow[0]*100
    dd = (ty[1]-ow[1])/ow[1]*100
    print(f"Δ typed vs owned: ΔPROMPT={dp:+6.2f}%  ΔDECODE={dd:+6.2f}%")

print()
print("Per-run prompt_tps (shuffled order):")
for m in modes:
    print(f"  {m:<8}: {[f'{x:.2f}' for x in data[m]['prompt_tps']]}")
print("Per-run decode_tps (shuffled order):")
for m in modes:
    print(f"  {m:<8}: {[f'{x:.2f}' for x in data[m]['decode_tps']]}")
EOF
