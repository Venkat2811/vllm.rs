# H100 Idle-Gap Semantics Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Scope: harness semantics only

## What changed

Serving and PD wrappers now have an explicit non-saturation submode:

- `serving_qos.cold_turn_idle_gap`
- `pd_qos.cold_turn_idle_gap`

Defaults for these submodes:

- no warmup-step first-turn skip
- `request_rate = 1.0`
- retained `arrival_pattern = configured_fixed_rate`
- small default request shape suitable for TTFT-focused idle-gap work

## Why it matters

The current bridge and QoS work no longer has to overload `request_rate` through
ad hoc shell overrides when the real question is "what happens when requests do not
arrive back-to-back?"

This creates an explicit semantics layer for future retained runs:

- saturation / zero-gap
- cold-turn / first-turn measured
- cold-turn with fixed-rate idle gaps
- warm steady state

## Validation

- `python3 -m unittest discover -s scripts/tests -v`
- `python3 -m py_compile scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py`

New tests prove:

- serving idle-gap mode sets `request_rate = 1.0`
- PD idle-gap mode sets `request_rate = 1.0`
- both modes keep `warmup_policy = measure_first_turn`
- both modes classify as `configured_fixed_rate`
