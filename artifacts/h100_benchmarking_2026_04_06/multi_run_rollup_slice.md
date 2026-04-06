# Multi-Run Rollup Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Repo: `vllm.rs`
Branch: `myelon-integration-1`

## Purpose

Land the first true multi-run rollup layer on top of retained benchmark campaigns.

Unlike the earlier per-campaign report-bundle work, this slice scans multiple retained `report.json` files and generates campaign-level summaries.

## What Changed

- added [`scripts/build_myelon_report_rollup.py`](/root/Documents/myelon-launch/vllm.rs/scripts/build_myelon_report_rollup.py)
- extended [`scripts/myelon_report_common.py`](/root/Documents/myelon-launch/vllm.rs/scripts/myelon_report_common.py) with:
  - legacy-report backfill
  - model-label inference
  - campaign-wide rollup generation

The rollup generator now writes:

- `reports/benchmarks/current_findings.{md,csv}`
- `reports/benchmarks/rollup_run_index.{md,csv}`
- `reports/benchmarks/per_model_side_by_side.{md,csv}`

## Historical Backfill

The retained `h100_quickpass_20260403_req10` campaign predates the newest contract fields.

This slice backfills enough semantics to make those historical artifacts readable:

- benchmark family
- benchmark submode
- topology overlay
- transport mode
- run class
- status
- model label
- model capability

That lets older retained runs participate in the new rollup layer without rewriting the original raw `report.json` files.

## Real Output Produced

The generator was run against:

```bash
python3 scripts/build_myelon_report_rollup.py --campaign-root artifacts/h100_quickpass_20260403_req10
```

Generated retained outputs now exist under:

- [`current_findings.md`](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/reports/benchmarks/current_findings.md)
- [`current_findings.csv`](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/reports/benchmarks/current_findings.csv)
- [`rollup_run_index.md`](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/reports/benchmarks/rollup_run_index.md)
- [`rollup_run_index.csv`](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/reports/benchmarks/rollup_run_index.csv)
- [`per_model_side_by_side.md`](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/reports/benchmarks/per_model_side_by_side.md)
- [`per_model_side_by_side.csv`](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/reports/benchmarks/per_model_side_by_side.csv)

## TDD Coverage

Validated with:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/build_myelon_report_rollup.py scripts/myelon_report_common.py scripts/myelon_validation_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```

New coverage now proves:

- Hugging Face cache paths are converted into readable model labels
- synthetic retained campaigns can be rolled up into:
  - current findings
  - rollup run index
  - per-model side-by-side outputs

## Current Boundary

This is the first multi-run rollup slice, not the final reporting layer.

Still open:

- higher-level narrative summaries like `all-model-results-and-run-commands.md`
- chart generation
- campaign-to-campaign filtering by benchmark family or run class
