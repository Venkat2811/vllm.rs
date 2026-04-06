# Server Prefill KV-Fraction Guard Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Problem

The new `server_prefill_stress` family introduced default KV-pressure shaping through `--kv-fraction`, but retained H100 bridge runs also wanted to set `VLLM_MAX_MODEL_LEN` explicitly.

`vllm-rs` rejects that combination:

- `--max-model-len`
- `--kv-fraction`

When both reached the server command together, the bridge run failed before benchmarking.

## Fix

The server wrapper now treats this conflict explicitly:

- if both `VLLM_MAX_MODEL_LEN` and `VLLM_SERVER_KV_FRACTION` are set explicitly, fail fast before launch
- if `server_prefill_stress` uses family-default `kv_fraction` and the user sets `VLLM_MAX_MODEL_LEN`, drop the default `kv_fraction`
- if `server_prefill_stress` keeps its default KV-pressure shaping, omit `--max-model-len`

## TDD Coverage

The script contract tests now prove:

- default `server_prefill_stress` runs omit `--max-model-len`
- explicit `VLLM_MAX_MODEL_LEN` drops default `kv_fraction`
- explicit `VLLM_MAX_MODEL_LEN` plus explicit `VLLM_SERVER_KV_FRACTION` fails before build or launch

## Why This Matters

This unblocks retained H100 bridge reruns without weakening the broader `server_prefill_stress` family semantics.
