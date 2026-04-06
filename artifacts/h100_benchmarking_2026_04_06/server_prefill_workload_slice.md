# Server Prefill Stress Workload Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## What Landed

The retained `server_prefill_stress` family is now backed by real wrapper behavior, not only contract labels.

Implemented in:

- `scripts/run_myelon_server_benchmark_matrix.py`
- `scripts/myelon_validation_common.py`
- `scripts/tests/test_benchmark_contract.py`

## New Built-In Workloads

- `artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_fixed_prompt_burst.json`
- `artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json`
- `artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json`

These use upstream `generate_conversations` input format instead of a custom generator.

## Default Wrapper Semantics

When `VLLM_SERVER_BENCHMARK_FAMILY=server_prefill_stress` and no overriding env vars are provided:

- `benchmark_submode=cache_thrash_round_robin`
- `warmup_step=false`
- `conversation_sampling=round_robin`
- `limit_min_tokens=8`
- `limit_max_tokens=8`
- `prefix_cache=true`
- `prefix_cache_max_tokens=4096`
- `kv_fraction=0.35`
- `cpu_mem_fold=0.1`
- `cache_pressure_profile=hard_thrash`

For `benchmark_submode=fixed_prompt_burst`:

- built-in workload switches to the fixed-prompt synthetic config
- `limit_min_tokens=1`
- `limit_max_tokens=1`
- `prefix_cache=false`
- `kv_fraction=0.55`
- `cpu_mem_fold=0.5`
- `cache_pressure_profile=relaxed`

For `benchmark_submode=shared_prefix_round_robin_control`:

- built-in workload switches to the shared-prefix synthetic config
- `prefix_cache=true`
- `prefix_cache_max_tokens=32768`
- `kv_fraction=0.55`
- `cpu_mem_fold=0.5`
- `cache_pressure_profile=bounded_prefix`

## Why This Matters

This turns the new bridge family into an executable benchmark lane:

- full HTTP server path remains in the loop
- decode is intentionally clamped low
- round-robin ordering maximizes reuse distance
- cache-pressure profile is explicit and retained in reports

That makes the next H100 rerun wave meaningful:

- `fixed_prompt_burst` is now the direct server-side analogue of the old prompt-heavy question
- `cache_thrash_round_robin` should expose whether large shared-memory wins survive through server mode
- `shared_prefix_round_robin_control` gives an immediate control case without inventing a custom scheduler

## Validation

The script-level contract suite is green:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/myelon_validation_common.py scripts/myelon_report_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```

New coverage proves:

- default `server_prefill_stress` picks the built-in cache-thrash workload
- default `server_prefill_stress` forwards round-robin and low-decode controls to the upstream benchmark
- default `server_prefill_stress` forwards KV-pressure knobs to `vllm-rs`
- `shared_prefix_round_robin_control` picks the shared-prefix built-in workload
- `fixed_prompt_burst` picks the fixed-prompt built-in workload
- retained `run_index` and summary reports now surface:
  - `conversation_sampling`
  - `limit_min_tokens`
  - `limit_max_tokens`
  - `cache_pressure_profile`
- matched CLI-vs-server comparison metadata now exists too:
  - `fixed_prompt_burst` on CLI `prefill_stress`
  - `fixed_prompt_burst` on server `server_prefill_stress`
  - both now carry `equivalence_group=fixed_prompt_burst_bridge`
