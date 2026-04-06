# Server-Prefill-Stress Contract Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## What Landed

The retained benchmark contract now supports a fourth benchmark family:

- `server_prefill_stress`

The shared contract now also carries:

- `cache_pressure_profile`

This slice is implemented in:

- `scripts/myelon_validation_common.py`
- `scripts/run_myelon_server_benchmark_matrix.py`
- `scripts/myelon_report_common.py`
- `scripts/tests/test_benchmark_contract.py`

## New Contract Behavior

- valid benchmark families now include:
  - `prefill_stress`
  - `server_prefill_stress`
  - `serving_qos`
  - `pd_qos`
- cache-pressure profile is explicit instead of implied
- the server wrapper can now be shaped with real KV-pressure knobs:
  - `VLLM_SERVER_PREFIX_CACHE`
  - `VLLM_SERVER_PREFIX_CACHE_MAX_TOKENS`
  - `VLLM_SERVER_KV_FRACTION`
  - `VLLM_SERVER_CPU_MEM_FOLD`
  - optional explicit `VLLM_CACHE_PRESSURE_PROFILE`

If no explicit profile is provided, the wrapper now infers one from the runtime knobs:

- `relaxed`
- `bounded_prefix`
- `swap_pressure`
- `hard_thrash`

## New Test Coverage

The script test suite now proves:

- the contract accepts `server_prefill_stress`
- cache-pressure profile inference can detect a `hard_thrash` shape
- the server wrapper can emit a retained `server_prefill_stress` report
- the server wrapper actually forwards the KV-pressure flags into the `vllm-rs` server command

## Why This Matters

This does not yet create the full cache-thrash workload by itself.

What it does do:

- makes the new bridge benchmark family real in code instead of RFC-only
- gives retained reports enough metadata to distinguish normal serving from intentionally prefill-dominant serving
- gives the server wrapper the actual knobs needed for the next rerun wave

## Validation

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/myelon_validation_common.py scripts/myelon_report_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```
