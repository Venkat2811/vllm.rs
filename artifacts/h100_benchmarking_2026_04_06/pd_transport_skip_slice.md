# PD Transport Skip Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Purpose

Extend retained PD skip semantics from architecture and topology into transport capability.

This closes an important reporting gap: a LocalIPC PD failure caused by missing GPU peer access should not be recorded as a generic benchmark failure.

## What Landed

- `scripts/myelon_validation_common.py`
  - `infer_pd_transport_mode(...)`
  - `query_gpu_p2p_status(...)`
  - `classify_pd_transport_capability(...)`
- `scripts/run_myelon_pd_benchmark_matrix.py`
  - retained PD reports now include `transport_capability`
  - unsupported transport cases short-circuit before `cargo build`
  - retained report status now includes `skipped_unsupported_transport`
- `scripts/myelon_report_common.py`
  - run-index and rollup rows now expose `transport_supported` and `transport_skip_reason`
- `scripts/tests/test_benchmark_contract.py`
  - helper coverage for LocalIPC peer-access classification
  - end-to-end retained skip-report coverage for unsupported transport

## Current Rule

- `pd_tcp`
  - considered transport-supported by default
- `pd_localipc_default` and `pd_localipc_explicit`
  - require NVIDIA P2P read and write status to be `OK` between the PD server GPU and PD client GPU
  - if not, retained reports emit an explicit transport skip reason
- unknown custom PD URL schemes
  - retained as unsupported transport until a dedicated contract exists

## Why This Matters

The Blackwell VM already proved this distinction matters:

- Myelon PD control-path correctness was fixed
- LocalIPC PD still failed because CUDA peer access was unavailable on that host

Those are very different conclusions. The retained reports now preserve that boundary explicitly.

## Validation

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
