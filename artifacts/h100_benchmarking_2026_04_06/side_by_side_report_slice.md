# Side-By-Side Report Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Repo: `vllm.rs`
Branch: `myelon-integration-1`

## Purpose

Extend the retained report bundle so each benchmark campaign produces both:

- a high-level run index
- a direct baseline versus Myelon side-by-side view

This slice is about report shape, not benchmark conclusions.

## What Changed

`scripts/myelon_report_common.py` now writes additional benchmark-report outputs:

- `reports/benchmarks/run_index.csv`
- `reports/benchmarks/run_index.md`
- `reports/benchmarks/per_variant_side_by_side.csv`
- `reports/benchmarks/per_variant_side_by_side.md`

The new files sit beside the earlier:

- `reports/benchmarks/run_summary.md`
- `reports/benchmarks/run_details.csv`

## Current Semantics

- `run_index.*` gives a compact one-row identity and status view for the current retained campaign
- `per_variant_side_by_side.*` compares the first baseline case against the first Myelon case when that pair exists
- if no runner or Myelon comparison pair exists, the side-by-side report is still emitted with an explicit note

This is enough to make single retained campaigns easier to analyze without manually diffing JSON.

## TDD Coverage

Validated with:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/myelon_report_common.py scripts/myelon_validation_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```

The existing script-level tests now prove that mocked CLI, serving, and PD runs emit:

- `run_summary.md`
- `run_details.csv`
- `run_index.md`
- `per_variant_side_by_side.md`
- system snapshot files

## Current Boundary

This slice improves per-campaign readability, but it is not yet the full reference-style rollup layer.

Still open:

- multi-run rollups across campaigns
- higher-level benchmark summaries across workload/model families
- charts or visual summaries
- stronger pairing logic when campaigns contain more than one baseline/Myelon pair
