# Benchmark Summary

| Key                     | Value                                                                                                                           |
|-------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | serving_qos                                                                                                                     |
| benchmark_submode       | cold_turn_idle_gap                                                                                                              |
| workload_class          | synthetic_multi_turn                                                                                                            |
| warmup_policy           | measure_first_turn                                                                                                              |
| first_turn_measured     | True                                                                                                                            |
| arrival_pattern         | configured_fixed_rate                                                                                                           |
| cache_pressure_profile  | relaxed                                                                                                                         |
| equivalence_group       |                                                                                                                                 |
| conversation_sampling   | round_robin                                                                                                                     |
| limit_min_tokens        |                                                                                                                                 |
| limit_max_tokens        |                                                                                                                                 |
| topology_overlay        | tp2                                                                                                                             |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                 |
| build_features          | cuda,myelon,nccl                                                                                                                |
| effective_device_ids    | [0, 1]                                                                                                                          |
| myelon_rpc_depth        | 8192                                                                                                                            |
| myelon_response_depth   | 8192                                                                                                                            |
| myelon_busy_spin        | True                                                                                                                            |
| prefix_cache_enabled    | False                                                                                                                           |
| prefix_cache_max_tokens |                                                                                                                                 |
| kv_fraction             |                                                                                                                                 |
| cpu_mem_fold            |                                                                                                                                 |
| run_class               | fullpass                                                                                                                        |
| stop_point              | full_completion                                                                                                                 |
| status                  | completed                                                                                                                       |
| expected_case_count     | 2                                                                                                                               |
| observed_case_count     | 2                                                                                                                               |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_tp2_cold_turn_idle_gap_v2/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label   |   latency_ms_mean |   requests_per_sec |   runtime_sec | skip_reason   | stop_point      |   tpot_ms_mean |   ttft_ms_mean |
|-----------------------|---------------|---------------------|---------|-------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner              | runner  |           241.337 |              1.791 |         3.909 |               | full_completion |          3.877 |        124.558 |
|                     0 | completed     | myelon              | myelon  |           247.723 |              1.787 |         3.917 |               | full_completion |          3.955 |        128.476 |
