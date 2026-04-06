# Bridge Benchmark Outcome Slice

Date: `2026-04-06`
Host: `hazy-instance-completes-fin-02`

## What changed

- retained server-bridge reports now parse benchmark-log outcome signals in addition to summary metrics and server-side cache pressure
- the new retained fields are:
  - `observed_successful_requests_total`
  - `observed_failed_requests_total`
  - `observed_clients_with_failures`
  - `observed_http_422_rejection_count`
- side-by-side reports and campaign rollups now carry those fields too

## Why this matters

- bridge runs can stop looking "complete" while still exercising very different effective workloads
- the new fields make it obvious when a cache-thrash run is actually running through request rejections and early client shutdown while the control run is not

## Current H100 bridge checkpoint

### `Qwen/Qwen3-0.6B` `tp2` `cache_thrash_round_robin`

- artifact:
  - `artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_cache_thrash_rr_v1`
- runner:
  - `2.447 req/s`
  - `7095.00 ms` TTFT
  - `12029.23 ms` latency
  - `39` successful requests
  - `3` failed requests
  - `9` HTTP `422` rejections
  - observed pressure: `requested_thrash_observed`
- myelon:
  - `2.335 req/s`
  - `6413.26 ms` TTFT
  - `12878.55 ms` latency
  - `54` successful requests
  - `2` failed requests
  - `8` HTTP `422` rejections
  - observed pressure: `requested_thrash_observed`

### `Qwen/Qwen3-0.6B` `tp2` `shared_prefix_round_robin_control`

- artifact:
  - `artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_shared_prefix_rr_control_v1`
- runner:
  - `3.376 req/s`
  - `2252.41 ms` TTFT
  - `9449.57 ms` latency
  - `160` successful requests
  - `0` failed requests
  - `0` HTTP `422` rejections
  - observed pressure: `requested_prefix_control_observed`
- myelon:
  - `3.343 req/s`
  - `2236.58 ms` TTFT
  - `9461.54 ms` latency
  - `160` successful requests
  - `0` failed requests
  - `0` HTTP `422` rejections
  - observed pressure: `requested_prefix_control_observed`

## Read

- the bridge lane is now more honest:
  - the strengthened shared-prefix control is clean and near parity
  - the heavy cache-thrash lane is not just "slower"; it is also rejection-heavy on both sides
- that means the next attribution slice should focus on explaining how request admission, cache pressure, swap behavior, and scheduler churn interact with the serving-path delta
