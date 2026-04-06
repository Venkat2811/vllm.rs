# H100 Medium-Model PD Slice And Model-Grouped Rollup Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Branch: `myelon-integration-1`

## Summary

Two useful H100 slices are now closed together:

- medium-model `pd_qos` fullpass on `Qwen/Qwen3-4B`
- grouped retained rollups by model for the active H100 campaigns

## Medium-Model PD Fullpass

Artifacts:

- `artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_cold_turn_idle_gap_v1`
- `artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1`

Results:

- `cold_turn_idle_gap`
  - runner PD: `1.164 req/s`, `331.445 ms` TTFT, `532.614 ms` latency
  - Myelon PD: `1.163 req/s`, `306.037 ms` TTFT, `509.719 ms` latency
  - read: throughput flat, TTFT and latency better under Myelon
- `warm_steady_state`
  - runner PD: `3.163 req/s`, `257.375 ms` TTFT, `497.185 ms` latency
  - Myelon PD: `3.215 req/s`, `265.975 ms` TTFT, `501.132 ms` latency
  - read: small throughput win, slight TTFT and latency regression

This is the first clean retained medium-model PD pair on the qualified H100 host. It means the H100 PD story is no longer only small-model or smoke-level.

## Model-Grouped Rollups

The retained rollup generator now emits:

- `reports/benchmarks/by_model/<model>/findings.{md,csv}`
- `reports/benchmarks/by_model/<model>/per_model_side_by_side.{md,csv}`

This closes the last obvious layout gap in the rollup tree:

- family
- workload
- topology
- run class
- result boundary
- artifact class
- pressure-outcome pair
- model

Applied campaigns:

- `artifacts/h100_idle_gap_campaign_20260406`
- `artifacts/h100_bridge_campaign_20260406`

## Read

The report layer is now good enough to stop treating artifact layout as the blocker.

The next 2-GPU work should stay on actual H100 execution:

- medium-model `serving_qos` fullpass on the qualified host
- any final 2-GPU `server_prefill_stress` conclusion that can be supported by retained attribution
- then defer only the genuine `tp4` / `tp8` / `pd+tp` expansion to bigger hosts
