# Unsupported-Skip Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Repo: `vllm.rs`
Branch: `myelon-integration-1`

## Purpose

Record the next `VR01` semantics-hardening slice after the initial contract and report-bundle work.

This slice makes one capability boundary explicit and testable:

- PD benchmarks now classify unsupported model architectures before benchmark execution
- the first concrete rule is hybrid Mamba or linear-attention state-transfer incompatibility
- unsupported PD runs now produce retained skip artifacts instead of looking like generic failures

## What Changed

- `scripts/myelon_validation_common.py`
  - added model-config loading and lightweight capability classification
- `scripts/run_myelon_benchmark_matrix.py`
  - now records `model_capability` and top-level `status` in retained reports
- `scripts/run_myelon_server_benchmark_matrix.py`
  - now records `model_capability` and top-level `status` in retained reports
- `scripts/run_myelon_pd_benchmark_matrix.py`
  - now classifies PD capability before build or benchmark execution
  - unsupported PD models short-circuit to:
    - `status = skipped_unsupported_architecture`
    - `benchmark_contract.skip_reason = unsupported_architecture_pd_state_transfer`
  - retained report bundles are still written for skipped runs
- `scripts/myelon_report_common.py`
  - higher-level summaries now expose top-level run `status`
  - per-case rows now expose `case_status`

## TDD Coverage

Validated with:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/myelon_report_common.py scripts/myelon_validation_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```

New test coverage now proves:

- hybrid linear-attention configs are detected as PD-incompatible
- unsupported PD models emit a retained skip report
- skip reports do not run `cargo build`
- normal CLI, serving, and PD mocked runs still report `status = completed`

## Current Boundary

This slice does not close `VR01` or `VR04`.

Still open:

- unsupported transport skip semantics
- unsupported topology skip semantics
- stronger cold-turn versus warm-steady-state semantics in serving and PD wrappers
- higher-level rollup reporting that groups skip, partial, and completed runs cleanly

## Why This Matters

The current benchmark history already includes structurally unsupported PD cases, especially hybrid Mamba models.

Those should be preserved as explicit skip datapoints, not as:

- benchmark regressions
- generic harness failures
- ambiguous partial artifacts
