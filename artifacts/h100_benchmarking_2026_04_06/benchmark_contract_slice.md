# Benchmark Contract Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Purpose

Record the first `VR01` implementation slice after the H100 clean-build gate.

This slice does not change benchmark behavior yet. It makes retained report semantics explicit across the current `vllm.rs` harness wrappers so later runs cannot be misread across benchmark families.

## Landed In Code

Shared helpers in `scripts/myelon_validation_common.py` now provide:

- benchmark-family contract construction
- run-class resolution and simple inference
- arrival-pattern classification
- workload-class inference from workload files
- machine-profile capture with host and GPU inventory

The current wrappers now emit `benchmark_contract` and `machine_profile` in their JSON reports:

- `scripts/run_myelon_benchmark_matrix.py`
- `scripts/run_myelon_server_benchmark_matrix.py`
- `scripts/run_myelon_pd_benchmark_matrix.py`

Per-case reports for serving and PD now also record:

- `execution_variant`
- `stop_point`
- `skip_reason`

## Current Contract Fields

The shared retained contract now includes:

- `benchmark_family`
- `benchmark_submode`
- `question_answered`
- `workload_class`
- `warmup_policy`
- `first_turn_measured`
- `arrival_pattern`
- `concurrency_policy`
- `topology_overlay`
- `transport_mode`
- `run_class`
- `stop_point`
- `skip_reason`

Machine capture now includes:

- hostname
- OS/platform
- CPU count
- CUDA-visible-device override
- compute-cap override
- detected CUDA device count
- effective device ids
- GPU inventory when `nvidia-smi` is available

## Validation

Commands run:

```bash
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile \
  scripts/myelon_validation_common.py \
  scripts/run_myelon_benchmark_matrix.py \
  scripts/run_myelon_server_benchmark_matrix.py \
  scripts/run_myelon_pd_benchmark_matrix.py \
  scripts/tests/test_benchmark_contract.py
```

Result:

- `5` contract-layer tests passed
- all touched Python files passed `py_compile`

## Boundary

This slice does not yet finish `VR01`.

Still open:

- explicit unsupported-skip classification for architecture, transport, and topology limits
- explicit cold vs warm submode labeling beyond the current warmup-step mapping
- stronger artifact summaries tied to retained benchmark runs
