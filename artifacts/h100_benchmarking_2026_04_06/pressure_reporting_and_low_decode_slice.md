# H100 Pressure Reporting And Low-Decode Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`

## What Landed

- retained cache-pressure evidence is now more explicit in `scripts/myelon_report_common.py`
- observed pressure is no longer just a coarse level:
  - `swap_engaged`
  - `high_gpu_pressure_no_swap`
  - `high_gpu_pressure_prefix_eviction`
  - lower-pressure fallback classes
- retained rows now also carry `pressure_profile_outcome`, so a run can say whether a requested profile was actually achieved or only partially realized
- rollup generation now emits a higher-level campaign report:
  - `reports/benchmarks/high_level_summary.md`
- `server_prefill_stress` now has a fourth executable bridge submode:
  - `low_decode`

## Why This Matters

- the active H100 bridge question is no longer just "did we request `swap_pressure`?"
- we need reports to answer the stronger question:
  - did the run actually engage CPU swap
  - or did it only reach GPU pressure without swap
  - or did it stay cache-friendly
- the added `high_level_summary.md` closes another gap versus the reference artifact style by surfacing wins, regressions, and incomplete or unsupported rows without forcing manual CSV review
- the new `low_decode` submode gives the bridge lane a lighter middle configuration between:
  - `fixed_prompt_burst`
  - `cache_thrash_round_robin`

## Validation

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/myelon_validation_common.py scripts/myelon_report_common.py scripts/run_myelon_server_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```

## Scope Boundary

- this slice is harness and reporting hardening only
- the live `swap_v10` retained benchmark result is intentionally not summarized here because it was still in flight while this code slice was landed
