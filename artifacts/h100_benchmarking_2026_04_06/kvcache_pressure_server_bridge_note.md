# KV-Cache Pressure And Server-Prefill-Stress Note

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Why This Note Exists

Current H100 results show two truths at once:

- CLI `prefill_stress` still surfaces a large Myelon prefill win on the old TP=2 prompt-heavy shape
- generic warmed serving QoS mostly compresses that down to TTFT wins and small throughput deltas

That means the next benchmark family cannot just be "more serving." It needs to keep the full server path in the loop while making prompt or prefill dominate again.

## Current `vllm.rs` Knobs That Control KV Pressure

The current codebase already exposes enough knobs to create meaningful cache pressure:

- `--kv-fraction`
  - GPU KV budget as a fraction of remaining GPU memory after model load
- `--max-model-len`
  - drives blocks per sequence
- `--max-num-seqs`
  - drives scheduler concurrency and overall KV demand
- `--prefix-cache`
  - enables automatic multi-turn prefix reuse
- `--prefix-cache-max-tokens`
  - hard cap on reusable prefix cache size
- `--cpu-mem-fold`
  - CPU KV swap budget relative to GPU KV budget

Relevant code and docs:

- `ReadMe.md`
- `docs/get_started.md`
- `src/utils/kvcache_allocator.rs`
- `src/core/scheduler.rs`
- `src/core/block_manager.rs`

## Important Current Behavior

### Allocator behavior

- If `--max-model-len` is set and `--kv-fraction` is omitted, allocator logic currently biases KV budget high by using `0.95` as the effective KV fraction.
- That is good for throughput and stability, but it is bad for a cache-thrash benchmark because it can accidentally make the GPU KV budget much more generous than intended.

### Prefix cache behavior

- Prefix cache can be enabled with `--prefix-cache`.
- Reusable prefix capacity can be bounded directly with `--prefix-cache-max-tokens`.
- Prefix cache and `--fp8-kvcache` are not compatible under the current flashinfer/flashattn settings.

### Pressure behavior

- The scheduler swap threshold is currently `95%` KV usage.
- Under pressure, scheduler logic first tries prefix-cache eviction and only then falls back to CPU swap.
- CPU swap capacity is derived from `--cpu-mem-fold` relative to GPU KV blocks.

Implication:

- if we want a serving benchmark that actually stresses the transport path, we need to pick a cache-pressure profile intentionally instead of inheriting defaults

## Recommended Cache-Pressure Profiles

### `relaxed`

Use when the goal is baseline realistic serving:

- generous `--kv-fraction`
- default or generous prefix cache
- normal `--cpu-mem-fold`

### `bounded_prefix`

Use when the goal is to keep prefix reuse present but obviously limited:

- `--prefix-cache`
- small `--prefix-cache-max-tokens`
- moderate `--kv-fraction`

### `swap_pressure`

Use when the goal is to pressure GPU KV and allow some CPU spill:

- reduced `--kv-fraction`
- moderate `--cpu-mem-fold`
- enough active conversations to keep old prefixes cold

### `hard_thrash`

Use when the goal is to make each progressive turn behave much closer to fresh prefill:

- reduced `--kv-fraction`
- tightly bounded `--prefix-cache-max-tokens`
- reduced `--cpu-mem-fold`
- round-robin request order across many conversations
- short decode so prompt effects do not disappear

## External Benchmark Reference

SGLang `benchmark/hicache` is the best local reference shape for this next lane.

Most useful idea:

- round-robin multiturn request order maximizes cache reuse distance

Control case:

- shared-prefix grouped order, where related requests stay together

Those two shapes should become paired workloads in the next server-side benchmark family.

## Current Planning Conclusion

The next bridge family should be `server_prefill_stress`:

- keep HTTP server and scheduler in the loop
- use low decode
- use explicit cache-pressure profiles
- compare cache-thrash round-robin against shared-prefix control
- aim to find at least one supported server-mediated scenario with a strong Myelon gain

If that still does not produce a large gain, the result should be an attribution artifact, not another ambiguous "serving was near parity" summary.
