# Report Bundle Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Purpose

Record the first retained-report layout slice inspired by the reference artifact structure.

The goal is not to claim benchmark results from this slice. The goal is to ensure future retained benchmark campaigns emit both machine-readable JSON and human-readable report bundles without needing later manual reconstruction.

## Landed In Code

Shared report generation now lives in:

- `scripts/myelon_report_common.py`

The current wrappers now emit a small `reports/` tree next to retained campaign JSON:

- `reports/system_info/system_snapshot.json`
- `reports/system_info/system_snapshot.csv`
- `reports/system_info/system_snapshot.md`
- `reports/benchmarks/run_summary.md`
- `reports/benchmarks/run_details.csv`

The generated system snapshot includes:

- machine profile
- repo state
- optional raw system-info capture references

The generated benchmark summary includes:

- benchmark family
- benchmark submode
- workload class
- topology overlay
- transport mode
- run class
- stop point
- per-case summary rows

## Validation

Commands run:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile \
  scripts/myelon_report_common.py \
  scripts/myelon_validation_common.py \
  scripts/run_myelon_benchmark_matrix.py \
  scripts/run_myelon_server_benchmark_matrix.py \
  scripts/run_myelon_pd_benchmark_matrix.py \
  scripts/tests/test_benchmark_contract.py
```

Result:

- `5` tests passed
- all touched Python files compiled cleanly

## Boundary

This slice creates the retained report bundle shape, but not the final full benchmark-analysis suite yet.

Still open:

- campaign-level run index across multiple retained runs
- richer Markdown summaries for side-by-side runner vs Myelon analysis
- per-family higher-level rollups similar to the reference `reports/benchmarks/*` set
