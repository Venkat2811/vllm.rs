# Benchmark Summary

| Key                    | Value                                                                                                                                       |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family       | server_prefill_stress                                                                                                                       |
| benchmark_submode      | shared_prefix_round_robin_control                                                                                                           |
| workload_class         | synthetic_server_shared_prefix_control                                                                                                      |
| warmup_policy          | measure_first_turn                                                                                                                          |
| first_turn_measured    | True                                                                                                                                        |
| arrival_pattern        | saturation_zero_gap                                                                                                                         |
| cache_pressure_profile | bounded_prefix                                                                                                                              |
| equivalence_group      |                                                                                                                                             |
| conversation_sampling  | round_robin                                                                                                                                 |
| limit_min_tokens       | 8                                                                                                                                           |
| limit_max_tokens       | 8                                                                                                                                           |
| topology_overlay       | tp2                                                                                                                                         |
| transport_mode         | socket_vs_myelon_process_runner                                                                                                             |
| run_class              | fullpass                                                                                                                                    |
| stop_point             | full_completion                                                                                                                             |
| status                 | completed                                                                                                                                   |
| expected_case_count    | 2                                                                                                                                           |
| observed_case_count    | 2                                                                                                                                           |
| report_json            | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v3/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label   | latency_ms_mean   |   requests_per_sec |   runtime_sec | skip_reason   | stop_point      | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|---------------|---------------------|---------|-------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner              | runner  |                   |              0.535 |       299.217 |               | full_completion |                |                |
|                     0 | completed     | myelon              | myelon  |                   |              0.523 |       306.027 |               | full_completion |                |                |
