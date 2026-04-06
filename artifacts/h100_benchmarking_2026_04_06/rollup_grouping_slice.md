# Rollup Grouping Slice

Date: 2026-04-06
Host class: H100 2x GPU benchmark host

## What changed

- `scripts/myelon_report_common.py` now emits grouped rollup trees beyond the earlier `by_family` and `by_equivalence` views.
- New grouped roots:
  - `reports/benchmarks/by_workload/`
  - `reports/benchmarks/by_topology/`
  - `reports/benchmarks/by_run_class/`
- `scripts/tests/test_benchmark_contract.py` now proves those grouped report bundles are created in addition to the existing family/equivalence views.

## Why this matters

- The active benchmark backlog is no longer only "flat campaign table plus one side-by-side view".
- H100 retained campaigns can now be sliced directly by:
  - workload class
  - topology overlay
  - run class
- This closes a real analysis gap for:
  - `server_prefill_stress` bridge work
  - separating `quickpass` from `fullpass`
  - comparing `single_gpu` vs `tp2` without shell-history reconstruction

## Regenerated campaigns

- `artifacts/h100_bridge_campaign_20260406`
- `artifacts/h100_quickpass_20260403_req10`

## Verification

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/myelon_report_common.py scripts/tests/test_benchmark_contract.py
```
