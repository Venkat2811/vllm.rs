# Tabulate Report Rendering Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Purpose

Stop hand-building Markdown tables in the active Python report generator and require `tabulate` directly.

## What Changed

- installed system `python3-pip`
- installed system `tabulate==0.10.0`
- `scripts/myelon_report_common.py` now imports `tabulate` directly
- retained Markdown tables now render through `tabulate(tablefmt="github")`

This applies to:

- system snapshot markdown
- benchmark summary markdown
- run-index markdown
- per-variant side-by-side markdown
- rollup markdown tables such as `current_findings`, `rollup_run_index`, and `per_model_side_by_side`

## Policy

- no non-`tabulate` fallback path was added
- if `tabulate` is missing, that is an environment problem, not a script-formatting branch

## Validation

```bash
python3 - <<'PY'
import tabulate
print(tabulate.__version__)
PY

python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile \
  scripts/myelon_report_common.py \
  scripts/myelon_validation_common.py \
  scripts/run_myelon_benchmark_matrix.py \
  scripts/run_myelon_server_benchmark_matrix.py \
  scripts/run_myelon_pd_benchmark_matrix.py \
  scripts/tests/test_benchmark_contract.py
```
