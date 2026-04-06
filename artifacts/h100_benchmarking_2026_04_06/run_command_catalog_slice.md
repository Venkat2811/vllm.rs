# Run Command Catalog Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Repo: `vllm.rs`
Branch: `myelon-integration-1`

## Purpose

Extend the new multi-run rollup layer with a retained command catalog.

The goal is to keep high-level benchmark summaries and exact run commands in the same report tree so later analysis does not depend on shell history reconstruction.

## What Changed

`scripts/build_myelon_report_rollup.py` now also writes:

- `reports/benchmarks/all_run_commands.md`

The file groups retained campaigns by:

- model label
- benchmark family
- topology overlay

and then records the available:

- `server_command`
- `pd_server_command`
- `client_server_command`
- `benchmark_command`
- generic `command`

## Real Output Produced

The retained `h100_quickpass_20260403_req10` campaign now includes:

- [`all_run_commands.md`](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/reports/benchmarks/all_run_commands.md)

## TDD Coverage

Validated with:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/build_myelon_report_rollup.py scripts/myelon_report_common.py scripts/myelon_validation_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```

The rollup test now proves the command-catalog file is emitted.

## Current Boundary

This is still report generation, not benchmark execution.

Still open:

- higher-level narrative command summaries
- command filtering by benchmark family or run class
- charting and visual rollups
