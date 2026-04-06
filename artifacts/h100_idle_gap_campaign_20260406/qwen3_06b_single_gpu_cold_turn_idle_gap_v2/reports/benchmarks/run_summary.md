# Benchmark Summary

| Key                     | Value                                                                                                                                  |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | serving_qos                                                                                                                            |
| benchmark_submode       | cold_turn_idle_gap                                                                                                                     |
| workload_class          | synthetic_multi_turn                                                                                                                   |
| warmup_policy           | measure_first_turn                                                                                                                     |
| first_turn_measured     | True                                                                                                                                   |
| arrival_pattern         | configured_fixed_rate                                                                                                                  |
| cache_pressure_profile  | relaxed                                                                                                                                |
| equivalence_group       |                                                                                                                                        |
| conversation_sampling   | round_robin                                                                                                                            |
| limit_min_tokens        |                                                                                                                                        |
| limit_max_tokens        |                                                                                                                                        |
| topology_overlay        | single_gpu                                                                                                                             |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                        |
| build_features          | cuda,myelon,nccl                                                                                                                       |
| effective_device_ids    |                                                                                                                                        |
| myelon_rpc_depth        | 8192                                                                                                                                   |
| myelon_response_depth   | 8192                                                                                                                                   |
| myelon_busy_spin        | False                                                                                                                                  |
| prefix_cache_enabled    | False                                                                                                                                  |
| prefix_cache_max_tokens |                                                                                                                                        |
| kv_fraction             |                                                                                                                                        |
| cpu_mem_fold            |                                                                                                                                        |
| run_class               | fullpass                                                                                                                               |
| stop_point              | full_completion                                                                                                                        |
| status                  | completed                                                                                                                              |
| expected_case_count     | 2                                                                                                                                      |
| observed_case_count     | 2                                                                                                                                      |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label   |   latency_ms_mean |   requests_per_sec |   runtime_sec | skip_reason   | stop_point      |   tpot_ms_mean |   ttft_ms_mean |
|-----------------------|---------------|---------------------|---------|-------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner              | runner  |           192.051 |              1.881 |         3.721 |               | full_completion |          3.833 |         75.543 |
|                     0 | completed     | myelon              | myelon  |           193.289 |              1.88  |         3.724 |               | full_completion |          3.84  |         76.525 |
