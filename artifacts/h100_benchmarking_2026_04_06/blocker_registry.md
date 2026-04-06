# H100 Blocker Registry And Stop-Point Policy

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Branch: `myelon-integration-1`

## Active Blockers

- PD unsupported for hybrid Mamba or linear-attention architectures
  - current example: `Qwen/Qwen3.5-27B-FP8`
- LocalIPC PD can be host-limited by CUDA peer-access support on some VMs
- upstream multi-turn benchmark still has an awkward partial-termination quirk on some bounded replay runs

## Resolved Blockers

- Myelon single-GPU server deadlock after request one
- PD helper verbs lost after Myelon handoff
- missing `nccl` in TP helper builds on Linux

## Acceptable Retained Stop Points

- unsupported architecture preflight
- unsupported topology preflight
- unsupported transport preflight
- host-limited LocalIPC data-plane failure after control-path success
- partial run that isolates a meaningful boundary clearly

## Unacceptable Retained Stop Points

- missing machine profile
- missing benchmark family
- stale-binary evidence after host change
- silent warmup behavior that changes the measured question without being recorded

## Rule

Every partial or skipped retained artifact must state:

- what stopped
- whether the stop is a useful datapoint
- what remains to reach full completion
