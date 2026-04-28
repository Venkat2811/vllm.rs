#!/usr/bin/env bash
# cleanup_mac_bench.sh — between-cell hygiene for Mac vllm.rs benches.
#
# Source from a bench script or call as a function. Idempotent.
# Cleans:
#   1. stale vllm-rs / runner processes (SIGTERM then SIGKILL)
#   2. /tmp leftovers from vllm-rs (cb_runner_*, mac_pd_smoke, etc.)
#   3. POSIX SHM segments under known myelon naming patterns
#   4. waits for TCP ports to drain TIME_WAIT
#
# Usage:
#   source scripts/lib/cleanup_mac_bench.sh
#   cleanup_between_cells [http_port_to_drain]

cleanup_between_cells() {
    local drain_port="${1:-}"
    local verbose="${VERBOSE_CLEANUP:-0}"

    # 1. Stale processes — SIGTERM, then SIGKILL after grace
    local pids
    pids=$(pgrep -f "vllm-rs|/release/runner" 2>/dev/null | grep -v "^$$\$" || true)
    if [[ -n "$pids" ]]; then
        [[ "$verbose" == "1" ]] && echo "[cleanup] SIGTERM to: $pids"
        echo "$pids" | xargs -r kill -TERM 2>/dev/null || true
        sleep 1
        # Anything still alive: force
        pids=$(pgrep -f "vllm-rs|/release/runner" 2>/dev/null | grep -v "^$$\$" || true)
        if [[ -n "$pids" ]]; then
            [[ "$verbose" == "1" ]] && echo "[cleanup] SIGKILL to: $pids"
            echo "$pids" | xargs -r kill -KILL 2>/dev/null || true
            sleep 1
        fi
    fi

    # 2. /tmp leftovers from competitive-bench style runs
    rm -rf /tmp/cb_runner_* 2>/dev/null
    rm -rf /tmp/mac_pd_* 2>/dev/null
    rm -f  /tmp/vllm_rs_*.log /tmp/myelon_*.log /tmp/heartbeat_* 2>/dev/null

    # 3. POSIX SHM cleanup. macOS doesn't expose /dev/shm, but Myelon /
    # vllm.rs name segments with predictable prefixes. We enumerate the
    # full set from the kernel via the only reliable mac mechanism:
    # `lsof -L1 | grep PSXSHM` to find segments held by no process,
    # then unlink them.
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PYEOF' 2>/dev/null
import subprocess, ctypes, ctypes.util, os
# Collect all PSXSHM segment names via lsof
try:
    out = subprocess.check_output(["lsof", "-c", "vllm-rs", "-c", "runner"],
                                  stderr=subprocess.DEVNULL).decode("utf-8", "ignore")
except Exception:
    out = ""
seen = set()
for line in out.splitlines():
    if "PSXSHM" not in line: continue
    parts = line.split()
    # Last column is the SHM name (often starting with '/')
    name = parts[-1] if parts else ""
    if name.startswith("/"):
        seen.add(name)
# Also try common naming patterns
for prefix in ("/myelon", "/vllm-rs", "/objs-"):
    pass  # can't enumerate by prefix on Mac without holders

if not seen:
    raise SystemExit(0)

libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
shm_unlink = libc.shm_unlink
shm_unlink.argtypes = [ctypes.c_char_p]
shm_unlink.restype = ctypes.c_int
for name in sorted(seen):
    rc = shm_unlink(name.encode())
    # silent — segment may already be unlinked
PYEOF
    fi

    # 4. Drain TCP TIME_WAIT for the bench port if specified
    if [[ -n "$drain_port" ]]; then
        local waited=0
        while lsof -nP -iTCP:"$drain_port" -sTCP:TIME_WAIT 2>/dev/null | grep -q .; do
            sleep 1
            waited=$((waited + 1))
            [[ $waited -ge 30 ]] && break
        done
    fi

    # 5. Tiny final settle
    sleep 1
}

# If invoked directly (not sourced), just run cleanup once.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cleanup_between_cells "${1:-}"
    echo "[cleanup] done"
fi
