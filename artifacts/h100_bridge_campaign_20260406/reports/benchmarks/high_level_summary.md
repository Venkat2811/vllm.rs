# High-Level Summary

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406`
- reports_found: `28`
- completed_runs: `24`
- incomplete_or_skipped_runs: `4`

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
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                |                 -8.5929 |                 5048.02 |               4614.25 | requested_thrash_not_observed       | requested_thrash_not_observed     |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                 -5.8981 |                14527.3  |              13670.5  | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                 -3.9982 |                 9854.32 |               9460.32 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                |                 -3.8061 |                 2616.56 |               2516.97 | requested_relaxed_observed          | requested_relaxed_observed        |

## Notable Regressions

| model_label        | benchmark_family      | benchmark_submode                 | topology_overlay   |   requests_per_sec_delta_percent |   baseline_requests_per_sec |   myelon_requests_per_sec | baseline_pressure_profile_outcome   | myelon_pressure_profile_outcome   |
|--------------------|-----------------------|-----------------------------------|--------------------|----------------------------------|-----------------------------|---------------------------|-------------------------------------|-----------------------------------|
| Qwen/Qwen3-0.6B    | server_prefill_stress | fixed_prompt_burst                | single_gpu         |                          -2.3638 |                      31.178 |                    30.441 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | shared_prefix_round_robin_control | tp2                |                          -2.243  |                       0.535 |                     0.523 | requested_prefix_control_observed   | requested_prefix_control_observed |
| Qwen/Qwen3-0.6B    | server_prefill_stress | fixed_prompt_burst                | tp2                |                          -2.1794 |                      30.788 |                    30.117 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-0.6B    | server_prefill_stress | fixed_prompt_burst                | single_gpu         |                          -1.8297 |                      15.248 |                    14.969 | requested_relaxed_observed          | requested_relaxed_observed        |
| Qwen/Qwen3-0.6B    | server_prefill_stress | fixed_prompt_burst                | tp2                |                          -1.765  |                      30.538 |                    29.999 | requested_relaxed_observed          | requested_relaxed_observed        |

## Incomplete / Unsupported

| model_label        | benchmark_family      | benchmark_submode        | topology_overlay   | status   | skip_reason   | report_json                                                                                                                             |
|--------------------|-----------------------|--------------------------|--------------------|----------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_swap_v9/report.json |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v1/report.json      |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | cache_thrash_round_robin | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v6/report.json      |
| Qwen/Qwen3-30B-A3B | server_prefill_stress | fixed_prompt_burst       | tp2                | partial  |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt/report.json            |
