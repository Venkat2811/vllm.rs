#!/usr/bin/env bash
# Hard-reset all vllm-rs/runner state between cells.
# Used by the orchestrator before/after each server start.
#
# What gets cleaned:
#   1. Stale processes (vllm-rs, runner subprocesses, bench client)
#   2. /dev/shm rings (Myelon SHM segments and PD c2s/s2c rings + their
#      _seq/_ci/_cr/_ad_*_seq/_producer_seq sidecar files)
#   3. Stale Unix-domain socket files (vllm-rs-runner-*.sock)
#   4. Stuck POSIX semaphores (myelon coord)
#
# Idempotent. Safe to run when nothing is up.

# Step 1: kill processes
# NOTE: do NOT pkill on "run_h200" — this script is invoked from run_h200_sweep.sh
# and would kill its own parent. Process names below are vllm-rs/runner only.
pkill -9 -f "vllm-rs --server"        >/dev/null 2>&1 || true
pkill -9 -f "vllm-rs --pd-server"     >/dev/null 2>&1 || true
pkill -9 -f "vllm-rs --pd-client"     >/dev/null 2>&1 || true
pkill -9 -f "binaries/.*/vllm-rs"     >/dev/null 2>&1 || true
pkill -9 -f "binaries/.*/runner "     >/dev/null 2>&1 || true
pkill -9 -f "/release/runner --sock"  >/dev/null 2>&1 || true
pkill -9 -f "bench_stress_sharegpt"   >/dev/null 2>&1 || true
sleep 2

# Verify nothing left
remaining=$(pgrep -af "vllm-rs|/release/runner" 2>/dev/null | wc -l)
if [ "$remaining" -gt 0 ]; then
  echo "[cleanup] WARN: $remaining stale procs still alive after pkill -9; trying again"
  pgrep -f "vllm-rs|/release/runner" | xargs -r kill -9 2>/dev/null || true
  sleep 1
fi

# Step 2: /dev/shm rings — cover every prefix we've ever produced
SHM_PATTERNS=(
  "vllm-rs-runner-*"
  "vllm-rs-pd-*"
  "myelon-*"
  "*@vllm-rs-runner-*"      # uuid-prefixed
  "command_*@vllm-rs-runner-*"
  "*_seq" "*_ci" "*_cr" "*_producer_seq" "*_ad_*_seq"
)
shm_removed=0
for pat in "${SHM_PATTERNS[@]}"; do
  for f in /dev/shm/$pat; do
    if [ -e "$f" ]; then
      rm -f "$f" 2>/dev/null && shm_removed=$((shm_removed + 1))
    fi
  done
done

# Step 3: socket files (abstract and filesystem)
# Abstract sockets disappear when the holder dies; filesystem sockets persist.
find /tmp /dev/shm -maxdepth 2 -name "*vllm-rs*" -type s -delete 2>/dev/null || true

# Step 4: POSIX semaphores in /dev/shm/sem.*
for f in /dev/shm/sem.*myelon* /dev/shm/sem.*vllm-rs*; do
  [ -e "$f" ] && rm -f "$f" 2>/dev/null
done

# Final state
gpu_used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | awk '{s+=$1} END {print s}')
shm_left=$(ls /dev/shm 2>/dev/null | grep -E "vllm-rs|myelon" | wc -l)
echo "[cleanup] gpu_used_total=${gpu_used}MB  shm_removed=${shm_removed}  shm_left=${shm_left}"
