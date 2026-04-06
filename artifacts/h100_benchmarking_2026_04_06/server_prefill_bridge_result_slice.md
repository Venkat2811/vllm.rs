# H100 Server-Prefill Bridge Result Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Campaign root: `artifacts/h100_bridge_campaign_20260406`

## Key retained bridge datapoints

### `qwen30ba3b_tp2_server_cache_thrash_rr_v8`

- family: `server_prefill_stress.cache_thrash_round_robin`
- requested profile: `hard_thrash`
- observed outcome:
  - runner: `high_gpu_pressure_no_swap`
  - myelon: `high_gpu_pressure_no_swap`
- observed peak GPU KV:
  - runner: `95.8%`
  - myelon: `97.3%`
- observed peak CPU swap:
  - runner: `0.0%`
  - myelon: `0.0%`
- result:
  - req/s: `0.369 -> 0.391` (`+5.96%`)
  - TTFT: worse by `+2.45%`
  - latency: better by `-2.75%`

### `qwen30ba3b_tp2_server_shared_prefix_rr_control_v3`

- family: `server_prefill_stress.shared_prefix_round_robin_control`
- requested profile: `bounded_prefix`
- observed outcome:
  - runner: `requested_prefix_control_observed`
  - myelon: `requested_prefix_control_observed`
- observed peak GPU KV:
  - runner: `38.0%`
  - myelon: `38.7%`
- observed peak CPU swap:
  - runner: `0.0%`
  - myelon: `0.0%`
- result:
  - req/s: `0.535 -> 0.523` (`-2.24%`)
  - TTFT: slightly worse by `+0.30%`
  - latency: worse by `+2.71%`

### `qwen30ba3b_tp2_server_cache_thrash_rr_swap_v10`

- family: `server_prefill_stress.cache_thrash_round_robin`
- requested profile: `swap_pressure`
- observed outcome:
  - runner: `requested_swap_not_observed`
  - myelon: `requested_swap_not_observed`
- observed peak GPU KV:
  - runner: `28.1%`
  - myelon: `18.9%`
- observed peak CPU swap:
  - runner: `0.0%`
  - myelon: `0.0%`
- result:
  - req/s: `0.344 -> 0.341` (`-0.87%`)
  - TTFT: `-32.70%`
  - latency: `+0.56%`

## Current read

- the bridge lane now clearly separates:
  - cache-friendly control
  - genuine GPU-pressure without swap
  - attempted swap-pressure that still failed to engage CPU swap
- requested `swap_pressure` is not enough by itself; current runtime plus workload shape can still stay entirely on GPU
- the largest serving-side signal in the latest `swap_v10` datapoint is TTFT, not throughput
- the next useful search is not another large-model rerun with the same shape; it is a smaller-model server-prefill hunt for a larger multiplicative serving gain, plus deeper attribution only if that hunt also stays compressed
