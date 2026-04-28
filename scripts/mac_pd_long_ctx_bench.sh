#!/usr/bin/env bash
# Mac M3 Max PD-mode long-context bench: socket vs Myelon-typed (KV=tcp) vs
# Myelon-typed (KV=Myelon SHM) at varying prompt lengths.
#
# Hypothesis: Myelon-KV vs TCP-KV was wash on Qwen3-0.6B (KV payload too small
# for transport bandwidth to matter). At long context the per-request KV
# transfer grows quadratically with sequence length × batch, and SHM
# bandwidth (~10+ GB/s) should dominate TCP loopback (~3 GB/s). This bench
# exists to find that crossover empirically.
#
# Methodology:
#   - Real ShareGPT prompts concatenated to target context length (4k/8k/16k).
#   - Open-loop bench client (bench_stress_sharegpt.py) for honest TTFT/p99.
#   - Each cell uses --force-runner so socket and Myelon paths are symmetric
#     (same subprocess topology, only the IPC transport differs).
#   - Cleanup between cells via lib/cleanup_mac_bench.sh.
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

# Compute MAXLEN as ceil(max_ctx * 1.2) + max_tokens, rounded to 1024.
# This needs to be >= the largest prompt we'll send.
MAX_BUCKET=$(echo "$CTX_BUCKETS" | tr ' ' '\n' | sort -n | tail -1)
MAXLEN=$(( (MAX_BUCKET * 6 / 5 + MAX_TOKENS + 1023) / 1024 * 1024 ))

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

OUT_DIR="$ROOT/scripts/mac_pd_long_ctx_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Model: $MODEL  reqs/cell: $NUM_REQS  concurrency: $CONCURRENCY  max_tokens: $MAX_TOKENS"
echo "Buckets: $CTX_BUCKETS  max_model_len: $MAXLEN"
echo "Ports: srv=$HTTP_S pd=$PD_PORT cli=$HTTP_C"
echo "Artifacts: $OUT_DIR"
echo ""

run_cell() {
    local label="$1" pd_url="$2" prompts_file="$3"; shift 3
    local extra=("$@")
    cleanup_between_cells "$HTTP_C"

    # Bound max-num-seqs to ~2*concurrency so KV cache budget at long context
    # doesn't OOM the unified-memory pool. Each side (server+client) sizes
    # its own KV cache to max-num-seqs × max-model-len, so at ctx=16k a
    # max-num-seqs=128 default would try to allocate ~180GB per side.
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

    # Warmup with the first prompt
    head -1 "$prompts_file" | python3 -c "
import json, sys, urllib.request
p = json.loads(sys.stdin.read())['prompt']
body = json.dumps({'model':'qwen3','messages':[{'role':'user','content':p}],'max_tokens':16}).encode()
req = urllib.request.Request('http://127.0.0.1:$HTTP_C/v1/chat/completions', data=body, headers={'Content-Type':'application/json'})
try: urllib.request.urlopen(req, timeout=300).read()
except Exception as e: print(f'warmup err: {e}', file=sys.stderr)
" >/dev/null 2>&1 || true

    # Use bench_stress_sharegpt.py for proper open-loop bench with TTFT.
    # macOS system Python is PEP-668-locked; uv handles the aiohttp dep
    # in an ephemeral venv (matches the H200 campaign scripts).
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

for ctx in $CTX_BUCKETS; do
    PROMPTS="$ROOT/scripts/long_ctx_buckets/sharegpt_${ctx}.jsonl"
    if [[ ! -f "$PROMPTS" ]]; then
        echo "❌ missing $PROMPTS — run build_long_context_buckets.py first"
        exit 1
    fi
    echo "═══ ctx=${ctx} ═══"

    echo "── pd_socket (KV=tcp) ──"
    run_cell "ctx${ctx}_socket" "tcp://127.0.0.1:$PD_PORT" "$PROMPTS" --force-runner || echo "  cell failed"
    echo ""

    echo "── pd_myelon_typed (KV=tcp) ──"
    run_cell "ctx${ctx}_myelon_typed" "tcp://127.0.0.1:$PD_PORT" "$PROMPTS" \
        --force-runner --myelon-ipc --myelon-access-mode typed || echo "  cell failed"
    echo ""

    echo "── pd_myelon_typed_kv (KV=Myelon SHM) ──"
    run_cell "ctx${ctx}_myelon_typed_kv" "myelon://default" "$PROMPTS" \
        --force-runner --myelon-ipc --myelon-access-mode typed || echo "  cell failed"
    echo ""
done

echo "═══ aggregate ═══"
python3 - <<EOF
import json, glob, os, statistics
out_dir = "$OUT_DIR"
data = {}
for path in sorted(glob.glob(os.path.join(out_dir, "*_results.json"))):
    with open(path) as f:
        d = json.load(f)
    name = os.path.basename(path).replace("_results.json","")
    s = d.get("summary", {})
    data[name] = {
        "ttft_p50":  s.get("ttft_ms_p50"),
        "ttft_p99":  s.get("ttft_ms_p99"),
        "lat_p50":   s.get("e2e_latency_ms_p50"),
        "lat_p99":   s.get("e2e_latency_ms_p99"),
        "req_per_s": s.get("requests_per_second"),
        "tok_per_s": s.get("output_tokens_per_second"),
    }

print(f"{'cell':<32} {'req/s':>8} {'tok/s':>8} {'ttft_p50':>10} {'ttft_p99':>10} {'lat_p50':>10} {'lat_p99':>10}")
print("-" * 90)
for name in sorted(data.keys()):
    d = data[name]
    fmt = lambda v: f"{v:>8.2f}" if v is not None else "       —"
    fmtl = lambda v: f"{v:>10.1f}" if v is not None else "         —"
    print(f"{name:<32} {fmt(d['req_per_s'])} {fmt(d['tok_per_s'])} {fmtl(d['ttft_p50'])} {fmtl(d['ttft_p99'])} {fmtl(d['lat_p50'])} {fmtl(d['lat_p99'])}")

# Δ vs socket per ctx
print()
print("Δ vs socket (Myelon variants):")
import re
ctxs = sorted({int(re.match(r"ctx(\d+)_", n).group(1)) for n in data if re.match(r"ctx\d+_", n)})
for ctx in ctxs:
    sk = data.get(f"ctx{ctx}_socket")
    if not sk or sk["lat_p50"] is None:
        continue
    print(f"  ctx={ctx}:")
    for variant in ("myelon_typed", "myelon_typed_kv"):
        cell = data.get(f"ctx{ctx}_{variant}")
        if not cell or cell["lat_p50"] is None:
            continue
        for k in ("req_per_s", "tok_per_s", "ttft_p50", "ttft_p99", "lat_p50", "lat_p99"):
            if cell[k] is None or sk[k] is None or sk[k] == 0:
                continue
            d = (cell[k] - sk[k]) / sk[k] * 100
            print(f"    {variant:<18} {k:<10}: socket={sk[k]:>8.2f}  v={cell[k]:>8.2f}  Δ={d:+6.1f}%")
EOF
