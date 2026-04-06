# High-Level Summary

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10`
- reports_found: `15`
- completed_runs: `15`
- incomplete_or_skipped_runs: `0`

## Strongest Requests/sec Gains

| model_label     | benchmark_family   | benchmark_submode   | topology_overlay   |   requests_per_sec_delta_percent |   baseline_requests_per_sec |   myelon_requests_per_sec | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|-----------------|--------------------|---------------------|--------------------|----------------------------------|-----------------------------|---------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | tp2                |                           6.9641 |                       3.116 |                     3.333 |                                     |                                   |
| Qwen/Qwen3-0.6B | serving_qos        | warm_steady_state   | single_gpu         |                           6.8376 |                       5.031 |                     5.375 |                                     |                                   |
| Qwen/Qwen3-0.6B | serving_qos        | warm_steady_state   | tp2                |                           5.0271 |                       4.615 |                     4.847 |                                     |                                   |
| Qwen/Qwen3-0.6B | pd_qos             | warm_steady_state   | pd_tp1             |                           4.5198 |                       0.708 |                     0.74  |                                     |                                   |
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | single_gpu         |                           2.8917 |                       2.974 |                     3.06  |                                     |                                   |

## Strongest TTFT Wins

| model_label     | benchmark_family   | benchmark_submode   | topology_overlay   |   ttft_ms_delta_percent |   baseline_ttft_ms_mean |   myelon_ttft_ms_mean | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|-----------------|--------------------|---------------------|--------------------|-------------------------|-------------------------|-----------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-0.6B | serving_qos        | warm_steady_state   | single_gpu         |                -24.2728 |                 162.462 |               123.028 |                                     |                                   |
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | tp2                |                -22.0556 |                 240.043 |               187.1   |                                     |                                   |
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | single_gpu         |                -17.1568 |                 145.995 |               120.947 |                                     |                                   |
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | single_gpu         |                -11.7877 |                 135.709 |               119.712 |                                     |                                   |
| Qwen/Qwen3-0.6B | pd_qos             | warm_steady_state   | pd_tp1             |                -11.583  |                 315.755 |               279.181 |                                     |                                   |

## Strongest Prompt Throughput Gains

| model_label     | benchmark_family   | benchmark_submode   | topology_overlay   |   prompt_tps_delta_percent |   baseline_prompt_tps_mean |   myelon_prompt_tps_mean | baseline_first_prefill_seconds_mean   | myelon_first_prefill_seconds_mean   |
|-----------------|--------------------|---------------------|--------------------|----------------------------|----------------------------|--------------------------|---------------------------------------|-------------------------------------|
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | single_gpu         |                    16.4623 |                    4350.42 |                  5066.6  |                                       |                                     |
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | tp2                |                    15.6186 |                    4504.07 |                  5207.54 |                                       |                                     |
| Qwen/Qwen3-4B   | serving_qos        | warm_steady_state   | tp2                |                    13.786  |                    2135.71 |                  2430.14 |                                       |                                     |
| Qwen/Qwen3-0.6B | serving_qos        | warm_steady_state   | tp2                |                     7.7878 |                    2694.03 |                  2903.84 |                                       |                                     |
| Qwen/Qwen3-0.6B | serving_qos        | warm_steady_state   | single_gpu         |                     6.4893 |                    6280.56 |                  6688.12 |                                       |                                     |

## Strongest Prefill-Roundtrip Wins

No prefill-roundtrip deltas were available.

## Strongest First-Prefill Wins

No first-prefill deltas were available.

## Notable Regressions

| model_label          | benchmark_family   | benchmark_submode   | topology_overlay   |   requests_per_sec_delta_percent |   baseline_requests_per_sec |   myelon_requests_per_sec | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|----------------------|--------------------|---------------------|--------------------|----------------------------------|-----------------------------|---------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-4B        | pd_qos             | warm_steady_state   | pd_tp1             |                          -0.9128 |                       2.958 |                     2.931 |                                     |                                   |
| Qwen/Qwen3-0.6B      | serving_qos        | warm_steady_state   | single_gpu         |                          -0.875  |                       0.8   |                     0.793 |                                     |                                   |
| Qwen/Qwen3.5-27B-FP8 | serving_qos        | warm_steady_state   | single_gpu         |                           0      |                       0.078 |                     0.078 |                                     |                                   |
| Qwen/Qwen3.5-27B-FP8 | serving_qos        | warm_steady_state   | tp2                |                           0      |                       0.141 |                     0.141 |                                     |                                   |
| Qwen/Qwen3-0.6B      | pd_qos             | warm_steady_state   | pd_tp1             |                           1.1833 |                       4.817 |                     4.874 |                                     |                                   |

## Incomplete / Unsupported

No incomplete or skipped runs.
