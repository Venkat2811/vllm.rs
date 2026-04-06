# High-Level Summary

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406`
- reports_found: `38`
- completed_runs: `34`
- incomplete_or_skipped_runs: `4`

## Pressure Outcome Pair Counts

| pressure_profile_outcome_pair                                          |   count |
|------------------------------------------------------------------------|---------|
| requested_prefix_control_observed -> requested_prefix_control_observed |       6 |
| requested_relaxed_exceeded -> requested_relaxed_exceeded               |       3 |
| requested_relaxed_observed -> requested_relaxed_observed               |      16 |
| requested_swap_not_observed -> none                                    |       1 |
| requested_swap_not_observed -> requested_swap_not_observed             |       1 |
| requested_thrash_not_observed -> none                                  |       1 |
| requested_thrash_not_observed -> requested_thrash_not_observed         |       5 |
| requested_thrash_observed -> requested_thrash_observed                 |       4 |

## Strongest Requests/sec Gains

| model_label        | benchmark_family      | benchmark_submode        | topology_overlay   |   requests_per_sec_delta_percent |   baseline_requests_per_sec |   myelon_requests_per_sec | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|--------------------|-----------------------|--------------------------|--------------------|----------------------------------|-----------------------------|---------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                          12.0976 |                       2.05  |                     2.298 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                           9.5102 |                      12.576 |                    13.772 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                |                           5.9621 |                       0.369 |                     0.391 | requested_thrash_observed           | requested_thrash_observed         |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                           5.4525 |                      10.839 |                    11.43  | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                           4.9331 |                      10.987 |                    11.529 | requested_relaxed_observed          | requested_relaxed_observed        |

## Strongest TTFT Wins

| model_label        | benchmark_family      | benchmark_submode        | topology_overlay   |   ttft_ms_delta_percent |   baseline_ttft_ms_mean |   myelon_ttft_ms_mean | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|--------------------|-----------------------|--------------------------|--------------------|-------------------------|-------------------------|-----------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                |                -32.6971 |                72898.7  |              49063    | requested_swap_not_observed         | requested_swap_not_observed       |
| Qwen/Qwen3-0.6B    | server_prefill_stress | cache_thrash_round_robin | tp2                |                 -9.6087 |                 7095    |               6413.26 | requested_thrash_observed           | requested_thrash_observed         |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                |                 -8.5929 |                 5048.02 |               4614.25 | requested_thrash_not_observed       | requested_thrash_not_observed     |
| Qwen/Qwen3-4B      | server_prefill_stress | cache_thrash_round_robin | tp2                |                 -6.4732 |                16483.3  |              15416.3  | requested_thrash_observed           | requested_thrash_observed         |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                 -5.8981 |                14527.3  |              13670.5  | requested_relaxed_observed          | requested_relaxed_observed        |

## Strongest Prompt Throughput Gains

| model_label        | benchmark_family      | benchmark_submode                 | topology_overlay   |   prompt_tps_delta_percent |   baseline_prompt_tps_mean |   myelon_prompt_tps_mean | baseline_first_prefill_seconds_mean   | myelon_first_prefill_seconds_mean   |
|--------------------|-----------------------|-----------------------------------|--------------------|----------------------------|----------------------------|--------------------------|---------------------------------------|-------------------------------------|
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin          | tp2                |                    44.1311 |                    127.298 |                  183.476 |                                       |                                     |
| Qwen/Qwen3-4B      | server_prefill_stress | cache_thrash_round_robin          | tp2                |                    33.6844 |                    417.843 |                  558.591 |                                       |                                     |
| Qwen/Qwen3-0.6B    | server_prefill_stress | cache_thrash_round_robin          | tp2                |                    27.932  |                   1190.66  |                 1523.24  |                                       |                                     |
| Qwen/Qwen3-4B      | server_prefill_stress | shared_prefix_round_robin_control | tp2                |                    20.4835 |                   1454.13  |                 1751.98  |                                       |                                     |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin          | tp2                |                    18.9364 |                    496.239 |                  590.209 |                                       |                                     |

## Strongest Prefill-Roundtrip Wins

| model_label        | benchmark_family      | benchmark_submode                 | topology_overlay   |   prefill_roundtrip_ms_delta_percent |   baseline_prefill_roundtrip_ms_mean |   myelon_prefill_roundtrip_ms_mean | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|--------------------|-----------------------|-----------------------------------|--------------------|--------------------------------------|--------------------------------------|------------------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-4B      | server_prefill_stress | shared_prefix_round_robin_control | tp2                |                             -12.4713 |                              4603.23 |                            4029.14 | requested_prefix_control_observed   | requested_prefix_control_observed |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | low_decode                        | tp2                |                              -9.513  |                             21934.8  |                           19848.2  | requested_relaxed_exceeded          | requested_relaxed_exceeded        |
| Qwen/Qwen3-4B      | server_prefill_stress | low_decode                        | tp2                |                              -1.8813 |                              7779.18 |                            7632.83 | requested_relaxed_exceeded          | requested_relaxed_exceeded        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst                | tp2                |                              -0.4878 |                             66850.6  |                           66524.5  | requested_relaxed_exceeded          | requested_relaxed_exceeded        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst                | tp2                |                              -0.411  |                              5926.97 |                            5902.61 | requested_relaxed_observed          | requested_relaxed_observed        |

## Strongest First-Prefill Wins

No first-prefill deltas were available.

## Notable Regressions

| model_label        | benchmark_family      | benchmark_submode                 | topology_overlay   |   requests_per_sec_delta_percent |   baseline_requests_per_sec |   myelon_requests_per_sec | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|--------------------|-----------------------|-----------------------------------|--------------------|----------------------------------|-----------------------------|---------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-4B      | server_prefill_stress | cache_thrash_round_robin          | tp2                |                          -5.3908 |                       1.113 |                     1.053 | requested_thrash_observed           | requested_thrash_observed         |
| Qwen/Qwen3-0.6B    | server_prefill_stress | cache_thrash_round_robin          | tp2                |                          -4.577  |                       2.447 |                     2.335 | requested_thrash_observed           | requested_thrash_observed         |
| Qwen/Qwen3-0.6B    | server_prefill_stress | fixed_prompt_burst                | single_gpu         |                          -2.3638 |                      31.178 |                    30.441 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | shared_prefix_round_robin_control | tp2                |                          -2.243  |                       0.535 |                     0.523 | requested_prefix_control_observed   | requested_prefix_control_observed |
| Qwen/Qwen3-4B      | server_prefill_stress | shared_prefix_round_robin_control | tp2                |                          -2.2161 |                       1.444 |                     1.412 | requested_prefix_control_observed   | requested_prefix_control_observed |

## Incomplete / Unsupported

| model_label        | benchmark_family      | benchmark_submode        | topology_overlay   | status   | skip_reason   | report_json                                                                                                                             |
|--------------------|-----------------------|--------------------------|--------------------|----------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_swap_v9/report.json |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v1/report.json      |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v6/report.json      |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt/report.json            |
