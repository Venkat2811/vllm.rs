#!/usr/bin/env bash
# Mac M3 Max — full matrix mirroring the H200 campaign methodology.
#
# Two phases:
#
# PHASE 1: CLI batch throughput (offline)
#   3 modes (socket, owned, typed) × 2 buckets (1k, 2k) × 4 batch sizes
#   × 3 repeats → median + IQR. Same shape as H200 phase11_bench_throughput.
#
# PHASE 2: HTTP server concurrency sweep (online)
#   3 modes × 1 bucket × concurrency [1, 4, 16, 64, 128] using a small
#   ad-hoc closed-loop client. Same shape as H200 phase 8.x closed_c*.
#
# Goal: match the H200 campaign's rigor on Mac so the comparison is
# apples-to-apples in METHODOLOGY (not in absolute hardware).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

BIN=./target/release/vllm-rs
MODEL=${MODEL:-Qwen/Qwen3-0.6B}
GGUF=${GGUF:-}
BATCHES=${BATCHES:-"8 32 64 128"}
BUCKETS=${BUCKETS:-"1k 2k"}
MAXTOK=${MAXTOK:-128}
MAXLEN=${MAXLEN:-2048}
REPEATS=${REPEATS:-3}
CONCS=${CONCS:-"1 4 16 64 128"}
NUM_REQS=${NUM_REQS:-50}

DATASET_DIR="${DATASET_DIR:-/Users/venkat/Documents/p/venkat-github/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign/datasets}"

if [[ -n "$GGUF" ]]; then
    MODEL_ARGS="--m $MODEL --f $GGUF"
    MODEL_TAG=$(basename "$GGUF" .gguf)
else
    MODEL_ARGS="--m $MODEL"
    MODEL_TAG=$(echo "$MODEL" | tr '/' '_')
fi

# Source between-cell cleanup so each bench cell starts from a clean slate
# (no stale vllm-rs procs, no leaked SHM segments, no TIME_WAIT sockets).
source "$SCRIPT_DIR/lib/cleanup_mac_bench.sh"

# QoS pinning notes (macOS):
#   `taskpolicy -c <clamp>` ONLY accepts utility / background / maintenance,
#   all of which DOWN-clamp the QoS (push toward E-cores). There is no
#   clamp value that forces P-cores upward — Apple's API is
#   "scheduler hint to deprioritise" only. Default (no clamp) lets the
#   kernel auto-pick, which biases CPU-heavy threads to P-cores.
#
#   So on Mac we leave the bench at default QoS. Real CPU pinning
#   (taskset / numactl / cpuset / isolcpus) is Linux-only and gets used
#   on the H200 box, not here.
#
#   To force E-cores (e.g. test how typed mode behaves under throttle):
#     PIN_QOS=utility ./mac_full_matrix_v2.sh
PIN_QOS="${PIN_QOS:-off}"
PIN_PREFIX=""
if [[ "$PIN_QOS" != "off" ]] && command -v taskpolicy >/dev/null 2>&1; then
    PIN_PREFIX="taskpolicy -c $PIN_QOS"
    echo "[pin] QoS clamp for vllm-rs invocations: $PIN_QOS (E-core bias)"
else
    echo "[pin] Default QoS (scheduler biases CPU-heavy work to P-cores)"
fi

OUT_DIR="$ROOT/scripts/mac_full_$(date +%Y%m%d_%H%M%S)_${MODEL_TAG}"
mkdir -p "$OUT_DIR"
echo "Artifacts: $OUT_DIR"
echo "Config: $MODEL ${GGUF:+gguf=$GGUF}  buckets=$BUCKETS  batches=$BATCHES  concs=$CONCS"
echo "        max_tok=$MAXTOK max_len=$MAXLEN repeats=$REPEATS num_reqs/cell=$NUM_REQS"
echo ""

# ─── Helpers ────────────────────────────────────────────────────────

pick_prompt() {
    local bucket="$1" min_tok="$2" max_tok="$3"
    python3 - <<EOF
import json, random
random.seed(42)
prompts = []
with open("$DATASET_DIR/sharegpt_${bucket}.jsonl") as f:
    for line in f:
        if not line.strip(): continue
        d = json.loads(line)
        n = d.get("input_tokens", 0)
        if $min_tok <= n <= $max_tok:
            prompts.append(d["prompt"])
        if len(prompts) >= 50: break
import re
p = random.choice(prompts) if prompts else "Tell me about distributed systems."
p = re.sub(r'\s+', ' ', p).replace('"', "'").strip()
print(p[:3500])
EOF
}

# ─── PHASE 1: CLI batch throughput ──────────────────────────────────

if [[ "${SKIP_PHASE1:-0}" == "1" ]]; then
    echo "SKIP_PHASE1=1, jumping straight to phase 2."
fi

if [[ "${SKIP_PHASE1:-0}" != "1" ]]; then
echo "═══════════════════════════════════════════════════════════════"
echo "  PHASE 1: CLI batch throughput (offline)"
echo "═══════════════════════════════════════════════════════════════"
mkdir -p "$OUT_DIR/phase1_cli"

run_cli() {
    local bucket="$1" batch="$2" run="$3" mode="$4"; shift 4
    local args=("$@")
    local log="$OUT_DIR/phase1_cli/${bucket}_b${batch}_run${run}_${mode}.log"
    "$BIN" $MODEL_ARGS --d 0 \
        --batch $batch --max-tokens $MAXTOK --max-model-len $MAXLEN \
        --prompts "$5" \
        "${args[@]}" 2>&1 > "$log" || echo "  ⚠ failed: $log"
    grep -E "Prompt tokens|Decoded tokens" "$log" | head -2
}

for bucket in $BUCKETS; do
    case "$bucket" in
        1k) PROMPT=$(pick_prompt 1k 900 1100) ;;
        2k) PROMPT=$(pick_prompt 2k 1900 2100) ;;
    esac
    echo "── bucket=$bucket  (prompt ${#PROMPT} chars) ──"

    for batch in $BATCHES; do
        echo "  batch=$batch:"
        for run in $(seq 1 $REPEATS); do
            echo "    run $run:"
            for mode in socket owned typed; do
                local_args=()
                case $mode in
                    socket) local_args=(--force-runner) ;;
                    owned)  local_args=(--force-runner --myelon-ipc --myelon-access-mode owned) ;;
                    typed)  local_args=(--force-runner --myelon-ipc --myelon-access-mode typed) ;;
                esac
                local_log="$OUT_DIR/phase1_cli/${bucket}_b${batch}_run${run}_${mode}.log"
                # Pre-cell hygiene: kill any stale procs, unlink leaked SHM
                cleanup_between_cells
                $PIN_PREFIX "$BIN" $MODEL_ARGS --d 0 \
                    --batch $batch --max-tokens $MAXTOK --max-model-len $MAXLEN \
                    --prompts "$PROMPT" \
                    "${local_args[@]}" > "$local_log" 2>&1 || echo "      ⚠ ${mode} failed"
                line=$(grep -E "Prompt tokens" "$local_log" | tail -1)
                line2=$(grep -E "Decoded tokens" "$local_log" | tail -1)
                echo "      $mode: ${line:30:80}  ${line2:30:60}"
            done
        done
    done
done

echo ""
echo "═══ Phase 1 aggregate ═══"
python3 - <<EOF
import re, glob, os, statistics

out_dir = "$OUT_DIR/phase1_cli"
data = {}  # (bucket, batch, mode) -> {prompt: [], decode: []}

for path in sorted(glob.glob(os.path.join(out_dir, "*.log"))):
    name = os.path.basename(path).replace(".log","")
    m = re.match(r"(1k|2k)_b(\d+)_run\d+_(socket|owned|typed)$", name)
    if not m: continue
    bucket, batch, mode = m.group(1), int(m.group(2)), m.group(3)
    text = open(path).read()
    pm = re.search(r"Prompt tokens:.*?\(([\d.]+) tokens/s\)", text)
    dm = re.search(r"Decoded tokens:.*?\(([\d.]+) tokens/s\)", text)
    key = (bucket, batch, mode)
    data.setdefault(key, {"prompt": [], "decode": []})
    if pm: data[key]["prompt"].append(float(pm.group(1)))
    if dm: data[key]["decode"].append(float(dm.group(1)))

print(f"{'bucket':<7}{'batch':>5} {'mode':>7} {'prompt_med':>11} {'decode_med':>11} {'p_min':>7} {'p_max':>7} {'d_min':>7} {'d_max':>7}")
print("-" * 78)
for key in sorted(data.keys()):
    bucket, batch, mode = key
    p = data[key]["prompt"]; d = data[key]["decode"]
    if not p: continue
    pmed = statistics.median(p); dmed = statistics.median(d) if d else 0
    pmin = min(p); pmax = max(p)
    dmin = min(d) if d else 0; dmax = max(d) if d else 0
    print(f"{bucket:<7}{batch:>5} {mode:>7} {pmed:>11.1f} {dmed:>11.1f} {pmin:>7.1f} {pmax:>7.1f} {dmin:>7.1f} {dmax:>7.1f}")
print()

print("Δ vs socket (typed and owned):")
buckets = sorted({k[0] for k in data.keys()})
for bucket in buckets:
    batches = sorted({k[1] for k in data.keys() if k[0] == bucket})
    print(f"  bucket={bucket}:")
    for batch in batches:
        sk = data.get((bucket, batch, "socket"))
        if not sk or not sk["prompt"]: continue
        sp = statistics.median(sk["prompt"]); sd = statistics.median(sk["decode"]) if sk["decode"] else 1
        for mode in ("owned", "typed"):
            cm = data.get((bucket, batch, mode))
            if not cm or not cm["prompt"]: continue
            mp = statistics.median(cm["prompt"]); md = statistics.median(cm["decode"]) if cm["decode"] else 0
            dp = (mp-sp)/sp*100; dd = (md-sd)/sd*100 if sd else 0
            print(f"    batch={batch:>3} {mode:>6}: ΔPROMPT={dp:+7.2f}%  ΔDECODE={dd:+7.2f}%")
EOF
fi  # end SKIP_PHASE1 guard

# ─── PHASE 2: HTTP server concurrency sweep ─────────────────────────

if [[ "${SKIP_PHASE2:-0}" == "1" ]]; then
    echo "SKIP_PHASE2=1, exiting after phase 1."
    exit 0
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  PHASE 2: HTTP server concurrency sweep (online)"
echo "═══════════════════════════════════════════════════════════════"
mkdir -p "$OUT_DIR/phase2_server"

# Find a free HTTP port for the server
for p in 18000 19000 20000 21000 22000; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { HTTP_PORT=$p; break; }
done
echo "server port: $HTTP_PORT"
echo ""

# Pull a bunch of prompts for the concurrency sweep (open-loop client
# rotates through them). PHASE2_CTX selects the bucket: 1k / 2k for the
# H200-shipped buckets, or 4096 / 8192 / 16384 for our local long-ctx
# buckets. Default 1k preserves prior brink-v3 behavior.
PHASE2_CTX=${PHASE2_CTX:-1k}
case "$PHASE2_CTX" in
    1k|1024)  PHASE2_BUCKET="$DATASET_DIR/sharegpt_1k.jsonl"; PHASE2_MIN=900;  PHASE2_MAX=1100 ;;
    2k|2048)  PHASE2_BUCKET="$DATASET_DIR/sharegpt_2k.jsonl"; PHASE2_MIN=1900; PHASE2_MAX=2700 ;;
    4096)     PHASE2_BUCKET="$ROOT/scripts/long_ctx_buckets/sharegpt_4096.jsonl"; PHASE2_MIN=3500; PHASE2_MAX=5500 ;;
    8192)     PHASE2_BUCKET="$ROOT/scripts/long_ctx_buckets/sharegpt_8192.jsonl"; PHASE2_MIN=7000; PHASE2_MAX=10000 ;;
    16384)    PHASE2_BUCKET="$ROOT/scripts/long_ctx_buckets/sharegpt_16384.jsonl"; PHASE2_MIN=14000; PHASE2_MAX=18000 ;;
    *) echo "ERROR: unknown PHASE2_CTX=$PHASE2_CTX (expected 1k|2k|4096|8192|16384)" >&2; exit 1 ;;
esac
echo "  phase2 ctx bucket: $PHASE2_BUCKET (range $PHASE2_MIN..$PHASE2_MAX)"

python3 - <<EOF > "$OUT_DIR/phase2_server/prompts.json"
import json, random
random.seed(42)
prompts = []
with open("$PHASE2_BUCKET") as f:
    for line in f:
        if not line.strip(): continue
        d = json.loads(line)
        if $PHASE2_MIN <= d.get("input_tokens", 0) <= $PHASE2_MAX:
            prompts.append(d["prompt"])
        if len(prompts) >= 100: break
random.shuffle(prompts)
json.dump(prompts, open("/dev/stdout", "w"))
EOF
echo "  prompts pool: $(python3 -c 'import json; print(len(json.load(open("'$OUT_DIR'/phase2_server/prompts.json"))))') prompts"
echo ""

run_server_cell() {
    local mode="$1" conc="$2"; shift 2
    local args=("$@")
    local label="${mode}_c${conc}"
    local server_log="$OUT_DIR/phase2_server/${label}_server.log"
    local client_log="$OUT_DIR/phase2_server/${label}_client.log"

    cleanup_between_cells "$HTTP_PORT"
    sleep 1

    # Boot server with the same QoS pinning as Phase 1 cells
    $PIN_PREFIX "$BIN" $MODEL_ARGS --d 0 --server --port $HTTP_PORT \
        --max-model-len $MAXLEN --max-num-seqs 128 \
        "${args[@]}" > "$server_log" 2>&1 &
    SERVER_PID=$!
    for i in $(seq 1 90); do
        curl -sf http://127.0.0.1:$HTTP_PORT/v1/models >/dev/null 2>&1 && break
        sleep 1
    done
    if ! curl -sf http://127.0.0.1:$HTTP_PORT/v1/models >/dev/null 2>&1; then
        echo "  ❌ ${label}: server did not come up"
        kill $SERVER_PID 2>/dev/null
        return 1
    fi

    # Closed-loop client: $NUM_REQS requests with $conc parallelism
    python3 - "$OUT_DIR/phase2_server/prompts.json" $HTTP_PORT $conc $NUM_REQS $MAXTOK > "$client_log" 2>&1 <<'PYEOF'
import json, sys, time, asyncio, urllib.request

prompts_file = sys.argv[1]; port = int(sys.argv[2]); conc = int(sys.argv[3])
n_reqs = int(sys.argv[4]); max_tok = int(sys.argv[5])
prompts = json.load(open(prompts_file))

async def one(idx, sem, results):
    p = prompts[idx % len(prompts)]
    body = json.dumps({"model":"qwen3","messages":[{"role":"user","content":p}],"max_tokens":max_tok}).encode()
    async with sem:
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                          data=body, headers={"Content-Type":"application/json"})
            await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=120).read())
            results.append(time.perf_counter() - t0)
        except Exception as e:
            results.append(-1)

async def main():
    sem = asyncio.Semaphore(conc)
    results = []
    t0 = time.perf_counter()
    await asyncio.gather(*[one(i, sem, results) for i in range(n_reqs)])
    wall = time.perf_counter() - t0
    ok = sorted(x*1000 for x in results if x > 0)
    n = len(ok)
    print(f"reqs={n_reqs} ok={n} wall_s={wall:.2f} req_per_s={n_reqs/wall:.3f}")
    if n:
        print(f"p50={ok[n//2]:.1f}ms p90={ok[int(n*0.9)]:.1f}ms p99={ok[min(int(n*0.99),n-1)]:.1f}ms mean={sum(ok)/n:.1f}ms")

asyncio.run(main())
PYEOF

    echo "  $(basename $client_log .log):"
    cat "$client_log" | sed 's/^/    /'
    kill $SERVER_PID 2>/dev/null
    cleanup_between_cells "$HTTP_PORT"
}

for mode in socket owned typed; do
    case $mode in
        socket) margs=(--force-runner) ;;
        owned)  margs=(--force-runner --myelon-ipc --myelon-access-mode owned) ;;
        typed)  margs=(--force-runner --myelon-ipc --myelon-access-mode typed) ;;
    esac
    for conc in $CONCS; do
        echo "── $mode  c=$conc ──"
        run_server_cell "$mode" "$conc" "${margs[@]}"
    done
done

echo ""
echo "═══ Phase 2 aggregate (concurrency sweep) ═══"
python3 - <<EOF
import re, glob, os

out_dir = "$OUT_DIR/phase2_server"
data = {}  # (mode, conc) -> {req_per_s, p50, p90, p99}
for path in sorted(glob.glob(os.path.join(out_dir, "*_client.log"))):
    name = os.path.basename(path).replace("_client.log","")
    m = re.match(r"(socket|owned|typed)_c(\d+)$", name)
    if not m: continue
    mode, conc = m.group(1), int(m.group(2))
    text = open(path).read()
    rps = re.search(r"req_per_s=([\d.]+)", text)
    p50 = re.search(r"p50=([\d.]+)ms", text)
    p90 = re.search(r"p90=([\d.]+)ms", text)
    p99 = re.search(r"p99=([\d.]+)ms", text)
    if rps:
        data[(mode, conc)] = {
            "rps": float(rps.group(1)),
            "p50": float(p50.group(1)) if p50 else 0,
            "p90": float(p90.group(1)) if p90 else 0,
            "p99": float(p99.group(1)) if p99 else 0,
        }

concs = sorted({k[1] for k in data.keys()})
print(f"{'c':>4}  {'sock_rps':>8} {'sock_p99':>9} | {'own_rps':>8} {'own_p99':>9} | {'typ_rps':>8} {'typ_p99':>9} | {'Δrps_t':>7} {'Δp99_t':>7}")
print("-" * 95)
for c in concs:
    s = data.get(("socket", c)); o = data.get(("owned", c)); t = data.get(("typed", c))
    s_rps = s["rps"] if s else 0; s_p99 = s["p99"] if s else 0
    o_rps = o["rps"] if o else 0; o_p99 = o["p99"] if o else 0
    t_rps = t["rps"] if t else 0; t_p99 = t["p99"] if t else 0
    drps = (t_rps-s_rps)/s_rps*100 if s_rps else 0
    dp99 = (t_p99-s_p99)/s_p99*100 if s_p99 else 0
    print(f"{c:>4}  {s_rps:>8.2f} {s_p99:>9.1f} | {o_rps:>8.2f} {o_p99:>9.1f} | {t_rps:>8.2f} {t_p99:>9.1f} | {drps:>+6.1f}% {dp99:>+6.1f}%")
EOF
