# Benchmark Summary

| Key                     | Value                                                                                                                          |
|-------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | pd_qos                                                                                                                         |
| benchmark_submode       | cold_turn_idle_gap                                                                                                             |
| workload_class          | synthetic_multi_turn                                                                                                           |
| warmup_policy           | measure_first_turn                                                                                                             |
| first_turn_measured     | True                                                                                                                           |
| arrival_pattern         | configured_fixed_rate                                                                                                          |
| cache_pressure_profile  | unspecified                                                                                                                    |
| equivalence_group       |                                                                                                                                |
| conversation_sampling   |                                                                                                                                |
| limit_min_tokens        |                                                                                                                                |
| limit_max_tokens        |                                                                                                                                |
| topology_overlay        | pd_tp1                                                                                                                         |
| transport_mode          | pd_tcp                                                                                                                         |
| build_features          | cuda,myelon,nccl                                                                                                               |
| effective_device_ids    |                                                                                                                                |
| myelon_rpc_depth        | 8192                                                                                                                           |
| myelon_response_depth   | 8192                                                                                                                           |
| myelon_busy_spin        | True                                                                                                                           |
| prefix_cache_enabled    |                                                                                                                                |
| prefix_cache_max_tokens |                                                                                                                                |
| kv_fraction             |                                                                                                                                |
| cpu_mem_fold            |                                                                                                                                |
| run_class               | fullpass                                                                                                                       |
| stop_point              | full_completion                                                                                                                |
| status                  | completed                                                                                                                      |
| expected_case_count     | 2                                                                                                                              |
| observed_case_count     | 2                                                                                                                              |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_pd_cold_turn_idle_gap_v1/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label     |   latency_ms_mean |   requests_per_sec |   runtime_sec | skip_reason   | stop_point      |   tpot_ms_mean |   ttft_ms_mean |
|-----------------------|---------------|---------------------|-----------|-------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner_pd           | runner_pd |            396.31 |              1.378 |         5.081 |               | full_completion |          3.5   |        291.125 |
|                     0 | completed     | myelon_pd           | myelon_pd |            395.17 |              1.362 |         5.14  |               | full_completion |          3.454 |        291.329 |
