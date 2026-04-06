# H100 Host Resume

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Branch: `myelon-integration-1`

## Why this exists

The earlier ondemand H100 benchmark host, `plain-bear-unfolds-fin-02`, was shut down during the active `server_prefill_stress` work.

This note records the resumed machine so retained evidence later in the same campaign is not incorrectly treated as if it all came from one hostname.

## Machine

- virtualization: `KVM`
- OS: `Ubuntu 24.04.4 LTS`
- kernel: `6.8.0-100-generic`
- CPU: `80` vCPUs, `AMD EPYC 9654 96-Core Processor`
- RAM: `363 GiB`
- swap: `0`
- root disk free at resume: about `107 GiB`

## GPU

- `2 x NVIDIA H100 80GB HBM3`
- driver: `580.126.09`
- CUDA: `13.0`
- inter-GPU link: `NV18`

## Rebuild Gate

The clean-build benchmark gate was rerun here:

- `myelon-playground`: `cargo clean`, then `cargo build -p myelon-playground`
- `vllm.rs`: `cargo clean`, then `CUDA_COMPUTE_CAP=90 cargo build --release --bin vllm-rs --bin runner --features cuda,myelon,nccl`

## Read

- retained H100 benchmark evidence on this date now spans two same-shape ondemand hosts
- the resumed host is valid for continued comparison because the machine class is unchanged and the clean-build gate was rerun
