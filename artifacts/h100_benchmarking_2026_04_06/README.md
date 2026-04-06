# H100 Benchmark Host Snapshot

Date: 2026-04-06
Hosts:

- initial H100 host: `plain-bear-unfolds-fin-02`
- resumed H100 host: `hazy-instance-completes-fin-02`

Branch: `myelon-integration-1`

## Purpose

Capture the current machine, GPU, and local model-cache state before the next retained `vllm.rs` benchmark wave, including the later same-shape H100 host used after the first ondemand machine was shut down.

## Machine

- virtualization: `KVM`
- OS: `Ubuntu 24.04.4 LTS`
- kernel: `6.8.0-100-generic`
- CPU: `80` vCPUs, `AMD EPYC 9654 96-Core Processor`
- RAM: `363 GiB`
- swap: `0`
- root disk free:
  - initial host: about `104 GiB`
  - resumed host: about `107 GiB`

## GPU

- `2 x NVIDIA H100 80GB HBM3`
- driver: `580.126.09`
- CUDA: `13.0`
- inter-GPU link: `NV18`
- both GPUs idle at snapshot time

## Hugging Face Cache

- total HF cache size: about `153 GiB`

Current useful local model pool:

- `Qwen/Qwen3-0.6B`
- `Qwen/Qwen3-4B`
- `Qwen/Qwen3.5-27B-FP8`
- `Qwen/Qwen3-30B-A3B`
- `Qwen/Qwen3-30B-A3B-Instruct-2507`

Current placeholder or incomplete entries:

- `Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4`
- `Qwen/Qwen3-1.7B`

## Current Decision

- do not clean HF cache yet
- do not download additional models yet
- first future cache-removal candidate, if space becomes tight:
  - `Qwen/Qwen3-30B-A3B-Instruct-2507`

Reason:

- the current cache already covers:
  - small and medium serving
  - a large dense or FP8 serving case
  - a large sparse reference case for transport-sensitive TP benchmarking

## Rebuild Gate

The recent branch history crossed multiple GPU architectures:

- B300 `sm_100f`
- Blackwell `sm_120f`
- H100 `sm_90`

So the next retained benchmark wave on this host should start from:

1. `cargo clean`
2. clean rebuild on H100
3. only then benchmark capture

Carried-over binaries from the earlier hosts should not be treated as benchmark evidence.

This gate was rerun after the later ondemand H100 host switch too.

## Next Benchmark-Planning Implication

Use capability-based model selection by benchmark family:

- `prefill_stress`
  - favor a transport-sensitive large reference model such as `Qwen/Qwen3-30B-A3B`
- `server_prefill_stress`
  - keep the HTTP server path in the loop, but use explicit KV-pressure profiles and low-decode workloads so prompt effects can still surface
- `serving_qos`
  - keep a stable small / medium / large serving ladder
- `pd_qos`
  - restrict to PD-compatible cached models

## Current Harness-Hardening Slice

The first `VR01` contract slice is now landed and validated:

- all three retained harness wrappers emit shared `benchmark_contract` metadata
- all three retained harness wrappers emit `machine_profile`
- serving and PD case reports now carry explicit `stop_point` and `skip_reason` fields

See:

- `artifacts/h100_benchmarking_2026_04_06/benchmark_contract_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/report_bundle_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/report_manifest_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/tabulate_report_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/idle_gap_semantics_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/idle_gap_results_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/unsupported_skip_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/side_by_side_report_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/pd_topology_skip_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/pd_transport_skip_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/multi_run_rollup_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/run_command_catalog_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/kvcache_pressure_server_bridge_note.md`
- `artifacts/h100_benchmarking_2026_04_06/server_prefill_contract_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/server_prefill_workload_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/server_prefill_cache_pressure_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/server_prefill_kv_fraction_guard_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/server_prefill_bridge_results_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/server_prefill_06b_attribution_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/server_path_attribution_4b_bridge_slice.md`
- `artifacts/h100_benchmarking_2026_04_06/model_workload_policy.md`
- `artifacts/h100_benchmarking_2026_04_06/blocker_registry.md`
