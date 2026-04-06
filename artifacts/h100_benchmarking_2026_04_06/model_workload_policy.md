# H100 Model And Workload Policy

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Purpose

Record the benchmark-family-specific model and workload policy used for retained `vllm.rs` work on the active H100 host.

## Family Policy

### `prefill_stress`

- primary model: `Qwen/Qwen3-30B-A3B`
- fallback model: `Qwen/Qwen3-4B`
- workload: fixed-prompt burst with minimal decode

### `server_prefill_stress`

- primary bridge model: `Qwen/Qwen3-30B-A3B`
- faster fallback model: `Qwen/Qwen3-4B`
- sensitivity model: `Qwen/Qwen3-0.6B`
- workloads:
  - `fixed_prompt_burst`
  - `cache_thrash_round_robin`
  - `shared_prefix_round_robin_control`

### `serving_qos`

- stable ladder:
  - `Qwen/Qwen3-0.6B`
  - `Qwen/Qwen3-4B`
  - `Qwen/Qwen3.5-27B-FP8`
- workloads:
  - bounded synthetic multi-turn
  - bounded ShareGPT replay

### `pd_qos`

- allowlist:
  - `Qwen/Qwen3-0.6B`
  - `Qwen/Qwen3-4B`
- conditional future candidate:
  - `Qwen/Qwen3-30B-A3B`
- denylist example:
  - `Qwen/Qwen3.5-27B-FP8`

## Why This Exists

Retained campaigns should justify their chosen model/workload pair by benchmark family instead of inheriting one global ladder by habit.
