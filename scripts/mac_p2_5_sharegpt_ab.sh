#!/usr/bin/env bash
# Mac M3 Max single-process A/B with ShareGPT prompts (no PD).
# socket / myelon-owned / myelon-typed at multiple batch sizes.
# Uses the H200 campaign's sharegpt_1k.jsonl prompt bucket.
#
# Goal: clean apples-to-apples vs the H200 campaign methodology.
# Single process eliminates PD's two-process complexity that the user
# called out as a possible bug source.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

BIN=./target/release/vllm-rs
MODEL=${MODEL:-Qwen/Qwen3-0.6B}
GGUF=${GGUF:-}
BATCHES=${BATCHES:-"8 32 64 128"}
MAXTOK=${MAXTOK:-128}
MAXLEN=${MAXLEN:-2048}
REPEATS=${REPEATS:-3}

DATASET="${DATASET:-/Users/venkat/Documents/p/venkat-github/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign/datasets/sharegpt_1k.jsonl}"

if [[ ! -f "$DATASET" ]]; then
    echo "ERROR: ShareGPT dataset not found at $DATASET" >&2
    exit 1
fi

# Pick a representative ~1024-token prompt from the bucket
PROMPT=$(python3 - <<EOF
import json, random
random.seed(42)
prompts = []
with open("$DATASET") as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            n = d.get("input_tokens", 0)
            if 900 <= n <= 1100:
                prompts.append(d["prompt"])
            if len(prompts) >= 50:
                break
p = random.choice(prompts)
# vllm-rs --prompts takes a single argument; strip any newlines/quotes
import re
p = re.sub(r'\s+', ' ', p).replace('"', "'").strip()
# Cap length so the shell arg doesn't blow up
print(p[:3500])
EOF
)
echo "Picked prompt: ${PROMPT:0:100}... (length $(echo -n "$PROMPT" | wc -c) chars)"
echo ""

# Build common args. If GGUF specified, use --f instead of --m
if [[ -n "$GGUF" ]]; then
    MODEL_ARGS="--m $MODEL --f $GGUF"
else
    MODEL_ARGS="--m $MODEL"
fi

OUT_DIR="$ROOT/scripts/mac_p2_5_sharegpt_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Artifacts: $OUT_DIR"
echo "Model: $MODEL${GGUF:+ GGUF=$GGUF}  batches: $BATCHES  max_tok=$MAXTOK  max_len=$MAXLEN  repeats=$REPEATS"
echo ""

run_cell() {
    local label="$1" mode="$2" batch="$3"; shift 3
    local args=("$@")
    local log="$OUT_DIR/${label}_b${batch}_${mode}.log"
    "$BIN" $MODEL_ARGS --d 0 \
        --batch $batch --max-tokens $MAXTOK --max-model-len $MAXLEN \
        --prompts "$PROMPT" \
        "${args[@]}" 2>&1 > "$log"
    grep -E "Prompt tokens|Decoded tokens" "$log" | head -2
}

for BATCH in $BATCHES; do
    echo "═══ batch=$BATCH ═══"
    for run in $(seq 1 $REPEATS); do
        echo "  run $run:"
        echo "    socket:"
        run_cell "run${run}" "socket" $BATCH --force-runner | sed 's/^/      /'
        echo "    owned:"
        run_cell "run${run}" "owned"  $BATCH --force-runner --myelon-ipc --myelon-access-mode owned | sed 's/^/      /'
        echo "    typed:"
        run_cell "run${run}" "typed"  $BATCH --force-runner --myelon-ipc --myelon-access-mode typed | sed 's/^/      /'
    done
    echo ""
done

echo "═══ Aggregate ═══"
python3 - <<EOF
import re, glob, os, statistics

out_dir = "$OUT_DIR"
data = {}  # (batch, mode) -> {prompt_tps: [], decode_tps: []}

for path in sorted(glob.glob(os.path.join(out_dir, "*.log"))):
    name = os.path.basename(path).replace(".log","")
    m = re.match(r"run\d+_b(\d+)_(socket|owned|typed)$", name)
    if not m: continue
    batch, mode = int(m.group(1)), m.group(2)
    text = open(path).read()
    pm = re.search(r"Prompt tokens:.*?\(([\d.]+) tokens/s\)", text)
    dm = re.search(r"Decoded tokens:.*?\(([\d.]+) tokens/s\)", text)
    key = (batch, mode)
    data.setdefault(key, {"prompt": [], "decode": []})
    if pm: data[key]["prompt"].append(float(pm.group(1)))
    if dm: data[key]["decode"].append(float(dm.group(1)))

batches = sorted({b for b, _ in data.keys()})
print()
print(f"{'batch':>5} {'mode':>7} {'prompt_tps_med':>14} {'decode_tps_med':>14} {'prompt_iqr':>11} {'decode_iqr':>11}")
print("-" * 70)
for b in batches:
    for m in ("socket", "owned", "typed"):
        d = data.get((b, m), {"prompt":[0],"decode":[0]})
        p = d["prompt"]; dec = d["decode"]
        pmed = statistics.median(p) if p else 0
        dmed = statistics.median(dec) if dec else 0
        piqr = (max(p) - min(p)) if len(p) > 1 else 0
        diqr = (max(dec) - min(dec)) if len(dec) > 1 else 0
        print(f"{b:>5} {m:>7} {pmed:>14.1f} {dmed:>14.1f} {piqr:>11.1f} {diqr:>11.1f}")
    print()

print("Δ vs socket (typed-vs-socket and owned-vs-socket):")
for b in batches:
    sk = data.get((b, "socket"), {"prompt":[0],"decode":[0]})
    if not sk["prompt"]: continue
    sp = statistics.median(sk["prompt"]); sd = statistics.median(sk["decode"])
    for m in ("owned", "typed"):
        cm = data.get((b, m))
        if not cm or not cm["prompt"]: continue
        mp = statistics.median(cm["prompt"]); md = statistics.median(cm["decode"])
        dp = (mp-sp)/sp*100 if sp else 0
        dd = (md-sd)/sd*100 if sd else 0
        print(f"  batch={b:>3} {m:>6}: ΔPROMPT={dp:+7.2f}%  ΔDECODE={dd:+7.2f}%")
EOF
