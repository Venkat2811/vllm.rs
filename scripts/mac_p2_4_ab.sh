#!/usr/bin/env bash
# Mac M3 Max A/B for RFC 0034 P2.4 (typed zero-copy prefill).
# Three modes at identical settings:
#   socket  : --force-runner             (Unix socket + bincode)
#   owned   : --myelon-ipc owned          (SHM + lease + to_owned)
#   typed   : --myelon-ipc typed          (SHM + lease + ArchivedSeqs zero-copy)
#
# Three repeats per mode for a noise estimate. Single-stream batch=8 prefill
# stress: each run does 8 prompts × 64 output tokens. Prompts hash to ~256
# input tokens via a deterministic seed string.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

BIN=./target/release/vllm-rs
MODEL=Qwen/Qwen3-0.6B
BATCH=8
MAXTOK=64
MAXLEN=2048
REPEATS=3

OUT_DIR="$ROOT/scripts/mac_p2_4_ab_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Artifacts: $OUT_DIR"
echo ""

run_one() {
    local label="$1"; shift
    local mode_label="$1"; shift
    local args=("$@")
    local log="$OUT_DIR/${label}_${mode_label}.log"
    "$BIN" --m "$MODEL" --d 0 \
        --batch $BATCH --max-tokens $MAXTOK --max-model-len $MAXLEN \
        --prompts "Tell me about distributed systems and shared memory." \
        "${args[@]}" 2>&1 | tee "$log" | grep -E "Prompt tokens|Decoded tokens|FirstTokenPath" | tail -5
    echo ""
}

for run in $(seq 1 $REPEATS); do
    echo "═══ Run $run / $REPEATS ═══"
    run_one "run${run}" "socket" --force-runner
    run_one "run${run}" "owned"  --force-runner --myelon-ipc --myelon-access-mode owned
    run_one "run${run}" "typed"  --force-runner --myelon-ipc --myelon-access-mode typed
done

echo "═══ Aggregate ═══"
python3 - <<EOF
import re, glob, os, statistics

out_dir = "$OUT_DIR"
modes = ["socket", "owned", "typed"]
data = {m: {"prompt_tps": [], "decode_tps": [], "ttft_ms": []} for m in modes}

for path in sorted(glob.glob(os.path.join(out_dir, "*.log"))):
    name = os.path.basename(path).replace(".log","")
    parts = name.split("_")
    mode = parts[-1]
    if mode not in modes: continue
    text = open(path).read()
    m_p = re.search(r"Prompt tokens:.*?\(([\d.]+) tokens/s\)", text)
    m_d = re.search(r"Decoded tokens:.*?\(([\d.]+) tokens/s\)", text)
    m_t = re.search(r"prefill_roundtrip_ms=(\d+)", text)
    if m_p: data[mode]["prompt_tps"].append(float(m_p.group(1)))
    if m_d: data[mode]["decode_tps"].append(float(m_d.group(1)))
    if m_t: data[mode]["ttft_ms"].append(int(m_t.group(1)))

print()
print(f"{'mode':<8} {'prompt_tps':>14} {'decode_tps':>14} {'prefill_ms':>12}")
print("-" * 52)
medians = {}
for m in modes:
    p = data[m]["prompt_tps"]; d = data[m]["decode_tps"]; t = data[m]["ttft_ms"]
    pm = statistics.median(p) if p else 0
    dm = statistics.median(d) if d else 0
    tm = statistics.median(t) if t else 0
    medians[m] = (pm, dm, tm)
    print(f"{m:<8} {pm:>14.2f} {dm:>14.2f} {tm:>12.1f}")

print()
print("Δ vs socket (median over $REPEATS runs):")
sk = medians["socket"]
for m in ["owned", "typed"]:
    cm = medians[m]
    if sk[0] > 0:
        dp = (cm[0]-sk[0])/sk[0]*100
        dd = (cm[1]-sk[1])/sk[1]*100
        dt = (cm[2]-sk[2])/sk[2]*100 if sk[2] > 0 else 0
        print(f"  {m:<6}: ΔPROMPT={dp:+6.2f}%  ΔDECODE={dd:+6.2f}%  ΔPREFILL_MS={dt:+6.2f}%")

print()
print("Δ typed vs owned (isolates the heap-allocation kill):")
ow = medians["owned"]; ty = medians["typed"]
if ow[0] > 0:
    dp = (ty[0]-ow[0])/ow[0]*100
    dd = (ty[1]-ow[1])/ow[1]*100
    dt = (ty[2]-ow[2])/ow[2]*100 if ow[2] > 0 else 0
    print(f"  typed vs owned: ΔPROMPT={dp:+6.2f}%  ΔDECODE={dd:+6.2f}%  ΔPREFILL_MS={dt:+6.2f}%")

print()
print("Per-run prompt_tps (variance check):")
for m in modes:
    print(f"  {m:<8}: {[f'{x:.2f}' for x in data[m]['prompt_tps']]}")
EOF
