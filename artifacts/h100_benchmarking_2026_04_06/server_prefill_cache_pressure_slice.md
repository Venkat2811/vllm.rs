# Server Prefill Cache Pressure Slice

Date: 2026-04-06
Primary host: `hazy-instance-completes-fin-02`
Previous host context: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Scope

Record the first retained `server_prefill_stress.cache_thrash_round_robin` result that actually reached high observed GPU KV pressure after strengthening the workload and wrapper defaults.

## What Changed

The earlier retained `cache_thrash_round_robin` runs were still too light:

- observed GPU KV usage stayed around `1%` to `5%`
- observed CPU swap usage stayed at `0%`
- retained pressure classification stayed `minimal_pressure`

To stop calling that lane "cache thrash" without evidence, the wrapper and built-in workloads were tightened:

- `num_clients=32`
- `max_active_conversations=64`
- `max_num_seqs=64`
- `max_num_requests=384`
- `prefix_cache_max_tokens=1024`
- `kv_fraction=0.08`
- `cpu_mem_fold=0.05`
- heavy synthetic inputs now use `synthetic_server_prefill_long_source.txt`

## Stop-Point Resolved

Retained run `qwen30ba3b_tp2_server_cache_thrash_rr_v6` stopped before useful execution because the upstream conversation generator exhausted the repeated `sonnet.txt` source while trying to build very long prompts.

That was a benchmark-input bug, not a server or Myelon bug.

The fix was to generate:

- `artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_long_source.txt`

and repoint both heavy round-robin workload templates at that file.

## First High-Pressure Result

Retained report:

- `artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v8/report.json`

Model and topology:

- model: `Qwen/Qwen3-30B-A3B`
- topology: `tp2`
- family: `server_prefill_stress`
- submode: `cache_thrash_round_robin`
- run class: `fullpass`

Observed pressure:

- baseline GPU KV max: `95.8%`
- myelon GPU KV max: `97.3%`
- baseline CPU swap max: `0.0%`
- myelon CPU swap max: `0.0%`
- retained pressure level:
  - baseline: `high_gpu_pressure`
  - myelon: `high_gpu_pressure`

Performance:

- runner: `0.369 req/s`, `43203.94 ms` TTFT, `72768.07 ms` latency
- myelon: `0.391 req/s`, `44262.03 ms` TTFT, `70769.65 ms` latency
- delta:
  - `+5.9621%` requests/sec
  - `+2.4491%` TTFT
  - `-2.7463%` latency

## Read

- this is the first retained server-prefill result in this campaign that clearly shows real GPU KV pressure rather than assumed pressure
- it still does not produce the hoped-for large serving-side Myelon gain
- importantly, it also still does not engage CPU swap

So the bridge-lane question is now narrower and better posed:

- large serving-side gains do not automatically appear once GPU KV pressure is high
- the next useful pressure experiment is not "more of the same hard_thrash"
- the next useful experiment is an explicit `swap_pressure` profile, or deeper server-path attribution if swap remains impossible to trigger cleanly

## Immediate Next Steps

- rerun `shared_prefix_round_robin_control` under the stronger `32/64/384` shaping to keep a fair control beside the heavier cache-thrash lane
- add a true `swap_pressure` retained profile instead of assuming reduced `cpu_mem_fold` is enough
- if swap still does not engage, add server-path attribution rather than continuing to guess from end-to-end metrics
