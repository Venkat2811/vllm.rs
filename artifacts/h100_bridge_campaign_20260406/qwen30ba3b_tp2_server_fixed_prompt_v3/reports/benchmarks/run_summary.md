# Benchmark Summary

| Key                    | Value                                                                                                                           |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family       | server_prefill_stress                                                                                                           |
| benchmark_submode      | fixed_prompt_burst                                                                                                              |
| workload_class         | synthetic_server_fixed_prompt_burst                                                                                             |
| warmup_policy          | measure_first_turn                                                                                                              |
| first_turn_measured    | True                                                                                                                            |
| arrival_pattern        | saturation_zero_gap                                                                                                             |
| cache_pressure_profile | relaxed                                                                                                                         |
| equivalence_group      | fixed_prompt_burst_bridge                                                                                                       |
| conversation_sampling  | round_robin                                                                                                                     |
| limit_min_tokens       | 1                                                                                                                               |
| limit_max_tokens       | 1                                                                                                                               |
| topology_overlay       | tp2                                                                                                                             |
| transport_mode         | socket_vs_myelon_process_runner                                                                                                 |
| run_class              | fullpass                                                                                                                        |
| stop_point             | full_completion                                                                                                                 |
| status                 | completed                                                                                                                       |
| report_json            | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v3/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label   |   latency_ms_mean |   requests_per_sec |   runtime_sec | skip_reason   | stop_point      |   tpot_ms_mean |   ttft_ms_mean |
|-----------------------|---------------|---------------------|---------|-------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner              | runner  |           2826.83 |             10.839 |         2.952 |               | full_completion |              0 |        2616.56 |
|                     0 | completed     | myelon              | myelon  |           2688.23 |             11.43  |         2.8   |               | full_completion |              0 |        2516.97 |
