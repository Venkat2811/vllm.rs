# Benchmark Summary

| Key                     | Value                                                                                                                      |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | prefill_stress                                                                                                             |
| benchmark_submode       | fixed_prompt_burst                                                                                                         |
| workload_class          | custom_prompt_env_burst                                                                                                    |
| warmup_policy           | cli_warmup_runs:1                                                                                                          |
| first_turn_measured     | True                                                                                                                       |
| arrival_pattern         | prompt_burst_serial_runs                                                                                                   |
| cache_pressure_profile  | unspecified                                                                                                                |
| equivalence_group       |                                                                                                                            |
| conversation_sampling   |                                                                                                                            |
| limit_min_tokens        |                                                                                                                            |
| limit_max_tokens        |                                                                                                                            |
| topology_overlay        | tp2                                                                                                                        |
| tp_scale_overlay        | tp2                                                                                                                        |
| prefill_tp_size         | 2                                                                                                                          |
| decode_tp_size          | 2                                                                                                                          |
| pd_enabled              | False                                                                                                                      |
| pd_role_layout          |                                                                                                                            |
| transport_mode          | socket_vs_myelon_process_runner                                                                                            |
| build_features          | cuda,myelon,nccl                                                                                                           |
| effective_device_ids    |                                                                                                                            |
| myelon_rpc_depth        | 8192                                                                                                                       |
| myelon_response_depth   | 8192                                                                                                                       |
| myelon_busy_spin        | True                                                                                                                       |
| prefix_cache_enabled    |                                                                                                                            |
| prefix_cache_max_tokens |                                                                                                                            |
| kv_fraction             |                                                                                                                            |
| cpu_mem_fold            |                                                                                                                            |
| run_class               | fullpass                                                                                                                   |
| result_boundary         | stop_point_limited                                                                                                         |
| stop_point              | first_prefill_completion                                                                                                   |
| status                  | completed                                                                                                                  |
| expected_case_count     |                                                                                                                            |
| observed_case_count     | 2                                                                                                                          |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1/report.json |

## Case Summary

|   benchmark_exit_code | case_status              | decode_seconds_mean   | decode_tps_mean   | execution_variant   |   first_prefill_seconds_mean |   first_prefill_tps_mean | label   | latency_ms_mean   |   prompt_seconds_mean |   prompt_tps_mean | requests_per_sec   | result_boundary    | runtime_sec   | skip_reason   | stop_point               | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|--------------------------|-----------------------|-------------------|---------------------|------------------------------|--------------------------|---------|-------------------|-----------------------|-------------------|--------------------|--------------------|---------------|---------------|--------------------------|----------------|----------------|
|                     0 | first_prefill_completion |                       |                   | runner              |                         2.42 |                    7.022 | runner  |                   |                  2.42 |             7.022 |                    | stop_point_limited |               |               | first_prefill_completion |                |                |
|                     0 | first_prefill_completion |                       |                   | myelon              |                         2.42 |                    7.03  | myelon  |                   |                  2.42 |             7.03  |                    | stop_point_limited |               |               | first_prefill_completion |                |                |
