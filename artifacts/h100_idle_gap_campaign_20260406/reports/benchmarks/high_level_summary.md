# High-Level Summary

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406`
- reports_found: `5`
- completed_runs: `5`
- incomplete_or_skipped_runs: `0`

## Pressure Outcome Pair Counts

| pressure_profile_outcome_pair                            |   count |
|----------------------------------------------------------|---------|
| requested_relaxed_observed -> requested_relaxed_observed |       2 |

## Strongest Requests/sec Gains

| model_label     | benchmark_family   | benchmark_submode   | topology_overlay   |   requests_per_sec_delta_percent |   baseline_requests_per_sec |   myelon_requests_per_sec | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|-----------------|--------------------|---------------------|--------------------|----------------------------------|-----------------------------|---------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-4B   | pd_qos             | warm_steady_state   | pd_tp1             |                           1.644  |                       3.163 |                     3.215 |                                     |                                   |
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | single_gpu         |                          -0.0532 |                       1.881 |                     1.88  | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-4B   | pd_qos             | cold_turn_idle_gap  | pd_tp1             |                          -0.0859 |                       1.164 |                     1.163 |                                     |                                   |
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | tp2                |                          -0.2233 |                       1.791 |                     1.787 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-0.6B | pd_qos             | cold_turn_idle_gap  | pd_tp1             |                          -1.1611 |                       1.378 |                     1.362 |                                     |                                   |

## Strongest TTFT Wins

| model_label     | benchmark_family   | benchmark_submode   | topology_overlay   |   ttft_ms_delta_percent |   baseline_ttft_ms_mean |   myelon_ttft_ms_mean | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|-----------------|--------------------|---------------------|--------------------|-------------------------|-------------------------|-----------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-4B   | pd_qos             | cold_turn_idle_gap  | pd_tp1             |                 -7.6658 |                 331.445 |               306.037 |                                     |                                   |
| Qwen/Qwen3-0.6B | pd_qos             | cold_turn_idle_gap  | pd_tp1             |                  0.0701 |                 291.125 |               291.329 |                                     |                                   |
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | single_gpu         |                  1.2999 |                  75.543 |                76.525 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | tp2                |                  3.1455 |                 124.558 |               128.476 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-4B   | pd_qos             | warm_steady_state   | pd_tp1             |                  3.3414 |                 257.375 |               265.975 |                                     |                                   |

## Strongest Prompt Throughput Gains

| model_label     | benchmark_family   | benchmark_submode   | topology_overlay   |   prompt_tps_delta_percent |   baseline_prompt_tps_mean |   myelon_prompt_tps_mean | baseline_first_prefill_seconds_mean   | myelon_first_prefill_seconds_mean   |
|-----------------|--------------------|---------------------|--------------------|----------------------------|----------------------------|--------------------------|---------------------------------------|-------------------------------------|
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | single_gpu         |                     0.2254 |                    6735.62 |                  6750.81 |                                       |                                     |
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | tp2                |                    -1.2597 |                    6494.68 |                  6412.86 |                                       |                                     |

## Strongest Prefill-Roundtrip Wins

No prefill-roundtrip deltas were available.

## Strongest First-Prefill Wins

No first-prefill deltas were available.

## Notable Regressions

| model_label     | benchmark_family   | benchmark_submode   | topology_overlay   |   requests_per_sec_delta_percent |   baseline_requests_per_sec |   myelon_requests_per_sec | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|-----------------|--------------------|---------------------|--------------------|----------------------------------|-----------------------------|---------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-0.6B | pd_qos             | cold_turn_idle_gap  | pd_tp1             |                          -1.1611 |                       1.378 |                     1.362 |                                     |                                   |
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | tp2                |                          -0.2233 |                       1.791 |                     1.787 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-4B   | pd_qos             | cold_turn_idle_gap  | pd_tp1             |                          -0.0859 |                       1.164 |                     1.163 |                                     |                                   |
| Qwen/Qwen3-0.6B | serving_qos        | cold_turn_idle_gap  | single_gpu         |                          -0.0532 |                       1.881 |                     1.88  | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-4B   | pd_qos             | warm_steady_state   | pd_tp1             |                           1.644  |                       3.163 |                     3.215 |                                     |                                   |

## Incomplete / Unsupported

No incomplete or skipped runs.
