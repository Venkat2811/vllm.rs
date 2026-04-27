#!/usr/bin/env bash
# Mac M3 Max PD-mode bench: 20 sequential chat completions
# socket vs Myelon-typed. KV transfer over TCP loopback (Mac POSIX SHM
# 31-char name limit blocks myelon:// PD URL on macOS — Linux-only).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

BIN=./target/release/vllm-rs
MODEL=${MODEL:-Qwen/Qwen3-0.6B}
NUM_REQS=${NUM_REQS:-20}

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

OUT_DIR="$ROOT/scripts/mac_pd_bench_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Model: $MODEL  reqs/cell: $NUM_REQS  ports: srv=$HTTP_S pd=$PD_PORT cli=$HTTP_C"
echo "Artifacts: $OUT_DIR"
echo ""

run_pd() {
    local label="$1"; shift
    local extra=("$@")
    pkill -f "vllm-rs --pd-" 2>/dev/null || true
    sleep 1

    "$BIN" --pd-server --port $HTTP_S --m $MODEL --d 0 \
        --max-model-len 1024 --pd-url tcp://127.0.0.1:$PD_PORT \
        "${extra[@]}" > "$OUT_DIR/${label}_server.log" 2>&1 &
    SERVER_PID=$!

    "$BIN" --server --pd-client --port $HTTP_C --m $MODEL --d 0 \
        --max-model-len 1024 --pd-url tcp://127.0.0.1:$PD_PORT \
        "${extra[@]}" > "$OUT_DIR/${label}_client.log" 2>&1 &
    CLIENT_PID=$!

    for i in $(seq 1 90); do
        curl -sf http://127.0.0.1:$HTTP_C/v1/models >/dev/null 2>&1 && break
        sleep 1
    done
    if ! curl -sf http://127.0.0.1:$HTTP_C/v1/models >/dev/null 2>&1; then
        echo "  ❌ ${label} client did not come up"
        kill $SERVER_PID $CLIENT_PID 2>/dev/null
        return 1
    fi

    # Warmup
    curl -sf http://127.0.0.1:$HTTP_C/v1/chat/completions \
        -H 'Content-Type: application/json' \
        -d '{"model":"qwen3","messages":[{"role":"user","content":"Warmup."}],"max_tokens":8}' \
        >/dev/null 2>&1 || true

    # Measured
    python3 - <<EOF > "$OUT_DIR/${label}_lats.txt"
import json, time, urllib.request

url = "http://127.0.0.1:$HTTP_C/v1/chat/completions"
body = json.dumps({
    "model": "qwen3",
    "messages": [{"role": "user", "content": "Tell me about distributed systems."}],
    "max_tokens": 64,
}).encode()
hdr = {"Content-Type": "application/json"}

lats = []
n_ok = 0
for i in range($NUM_REQS):
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, data=body, headers=hdr, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            if "choices" in data:
                n_ok += 1
        lats.append(time.perf_counter() - t0)
    except Exception as e:
        lats.append(-1)
        print(f"req {i}: error {e}")

ok_lats = [x*1000 for x in lats if x > 0]
ok_lats.sort()
n = len(ok_lats)
print(f"requests: {$NUM_REQS}  ok: {n_ok}")
print(f"p50: {ok_lats[n//2]:.1f} ms")
print(f"p90: {ok_lats[int(n*0.9)]:.1f} ms")
print(f"p99: {ok_lats[min(int(n*0.99), n-1)]:.1f} ms")
import statistics
print(f"mean: {statistics.mean(ok_lats):.1f} ms")
print(f"all_lats: {[round(x,1) for x in ok_lats]}")
EOF
    cat "$OUT_DIR/${label}_lats.txt"
    kill $SERVER_PID $CLIENT_PID 2>/dev/null
    sleep 2
    pkill -f "vllm-rs --pd-" 2>/dev/null || true
    sleep 1
}

echo "── pd_socket ──"
run_pd "pd_socket"
echo ""
echo "── pd_myelon_typed ──"
run_pd "pd_myelon_typed" --force-runner --myelon-ipc --myelon-access-mode typed

echo ""
echo "── Δ (typed vs socket, end-to-end latency) ──"
python3 - <<EOF
import re

def parse(path):
    text = open(path).read()
    return {
        "p50": float(re.search(r"p50: ([\d.]+) ms", text).group(1)),
        "p90": float(re.search(r"p90: ([\d.]+) ms", text).group(1)),
        "p99": float(re.search(r"p99: ([\d.]+) ms", text).group(1)),
        "mean": float(re.search(r"mean: ([\d.]+) ms", text).group(1)),
    }

s = parse("$OUT_DIR/pd_socket_lats.txt")
t = parse("$OUT_DIR/pd_myelon_typed_lats.txt")
for k in ("p50", "p90", "p99", "mean"):
    d = (t[k] - s[k]) / s[k] * 100
    print(f"  {k}: socket={s[k]:.1f}ms  typed={t[k]:.1f}ms  Δ={d:+.1f}%")
EOF
