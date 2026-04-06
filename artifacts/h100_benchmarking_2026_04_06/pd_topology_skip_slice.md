# PD Topology Skip Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Repo: `vllm.rs`
Branch: `myelon-integration-1`

## Purpose

Extend retained PD benchmark semantics beyond architecture-based skips.

This slice adds topology-based skip classification so the PD wrapper can preserve unsupported host or device-role layouts as retained artifacts instead of aborting before a report exists.

## What Changed

- `scripts/myelon_validation_common.py`
  - added `classify_pd_topology_capability(...)`
- `scripts/run_myelon_pd_benchmark_matrix.py`
  - now records `topology_capability`
  - now classifies unsupported topology before `cargo build`
  - unsupported PD topologies emit retained `skipped_unsupported_topology` reports

The first topology skip reasons are:

- `unsupported_topology_pd_requires_explicit_single_device_roles`
- `unsupported_topology_pd_requires_single_device_server_and_client`
- `unsupported_topology_pd_requires_distinct_server_client_devices`
- `unsupported_topology_insufficient_visible_cuda_devices`

## TDD Coverage

Validated with:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile scripts/myelon_report_common.py scripts/myelon_validation_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py
```

New coverage now proves:

- topology capability classification catches insufficient visible GPUs
- unsupported PD topology writes a retained skip report
- unsupported PD topology skips `cargo build`
- normal PD retained reports now include `topology_capability`

## Current Boundary

This still does not close transport semantics.

Still open:

- transport-specific skip rules
- future peer-access probing for LocalIPC same-node PD
- broader multi-run rollups that summarize skipped topology cases across campaigns
