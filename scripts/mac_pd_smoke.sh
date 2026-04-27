#!/usr/bin/env bash
# Mac M3 Max PD-mode smoke. Server + client share single Metal GPU,
# KV transfer over TCP loopback (LocalIPC requires CUDA).
# Tests whether typed-mode applies to the PD path on Mac.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

BIN=./target/release/vllm-rs
MODEL=Qwen/Qwen3-0.6B

# Find free ports (Cursor / other dev tools eat 7000-12000)
for p in 18000 19000 20000 21000 22000; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { HTTP_S=$p; break; }
done
for p in 18001 19001 20001 21001 22001; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { PD_PORT=$p; break; }
done
for p in 18002 19002 20002 21002 22002; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { HTTP_C=$p; break; }
done
echo "ports: server-http=$HTTP_S  pd-tcp=$PD_PORT  client-http=$HTTP_C"
echo ""

LOG_DIR=/tmp/mac_pd_smoke
mkdir -p $LOG_DIR

run_pd_pair() {
    local mode="$1"
    local label="$2"
    local extra=("${@:3}")
    echo "── $label ──"

    # Clean any leftovers
    pkill -f "vllm-rs --pd-" 2>/dev/null || true
    sleep 1

    # Start prefill server (pd-server)
    "$BIN" --pd-server --port $HTTP_S --m $MODEL --d 0 \
        --max-model-len 1024 --pd-url tcp://127.0.0.1:$PD_PORT \
        "${extra[@]}" > $LOG_DIR/${label}_server.log 2>&1 &
    SERVER_PID=$!

    # Start decode client (pd-client + http server)
    "$BIN" --server --pd-client --port $HTTP_C --m $MODEL --d 0 \
        --max-model-len 1024 --pd-url tcp://127.0.0.1:$PD_PORT \
        "${extra[@]}" > $LOG_DIR/${label}_client.log 2>&1 &
    CLIENT_PID=$!

    # Wait for client HTTP to come up
    for i in $(seq 1 60); do
        if curl -sf http://127.0.0.1:$HTTP_C/v1/models >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    if ! curl -sf http://127.0.0.1:$HTTP_C/v1/models >/dev/null 2>&1; then
        echo "  ❌ client HTTP did not come up; tail of logs:"
        echo "  --- server ---"
        tail -5 $LOG_DIR/${label}_server.log | sed 's/^/    /'
        echo "  --- client ---"
        tail -5 $LOG_DIR/${label}_client.log | sed 's/^/    /'
        kill $SERVER_PID $CLIENT_PID 2>/dev/null || true
        return 1
    fi
    echo "  ✓ client HTTP up on port $HTTP_C"

    # Send 5 sequential chat requests, measure TTFT-ish (curl total)
    local total=0
    for i in 1 2 3 4 5; do
        local t0=$(python3 -c "import time;print(time.time())")
        local resp=$(curl -sf http://127.0.0.1:$HTTP_C/v1/chat/completions \
            -H 'Content-Type: application/json' \
            -d '{"model":"qwen3","messages":[{"role":"user","content":"Tell me about distributed systems."}],"max_tokens":32,"stream":false}' 2>&1)
        local t1=$(python3 -c "import time;print(time.time())")
        local ms=$(python3 -c "print(int(($t1-$t0)*1000))")
        if [[ -z "$resp" ]] || [[ "$resp" != *"choices"* ]]; then
            echo "    req $i: FAILED (${ms}ms)"
        else
            echo "    req $i: ${ms}ms"
        fi
        total=$((total + ms))
    done
    echo "  total: ${total}ms over 5 reqs"

    kill $SERVER_PID $CLIENT_PID 2>/dev/null || true
    sleep 2
    pkill -f "vllm-rs --pd-" 2>/dev/null || true
    sleep 1
}

run_pd_pair "socket" "pd_socket"
run_pd_pair "myelon-typed" "pd_myelon_typed" --force-runner --myelon-ipc --myelon-access-mode typed

echo ""
echo "Logs: $LOG_DIR/"
