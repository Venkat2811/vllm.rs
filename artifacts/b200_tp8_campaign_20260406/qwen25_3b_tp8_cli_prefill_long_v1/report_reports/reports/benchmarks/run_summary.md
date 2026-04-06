# Benchmark Summary

| Key                        | Value                                                                                                                    |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | prefill_stress                                                                                                           |
| benchmark_submode          | fixed_prompt_burst                                                                                                       |
| workload_class             | synthetic_prompt_long_stress_burst                                                                                       |
| warmup_policy              | cli_warmup_runs:1                                                                                                        |
| first_turn_measured        | True                                                                                                                     |
| arrival_pattern            | prompt_burst_serial_runs                                                                                                 |
| cache_pressure_profile     | unspecified                                                                                                              |
| equivalence_group          |                                                                                                                          |
| conversation_sampling      |                                                                                                                          |
| limit_min_tokens           |                                                                                                                          |
| limit_max_tokens           |                                                                                                                          |
| topology_overlay           | tp8                                                                                                                      |
| tp_scale_overlay           | tp8                                                                                                                      |
| prefill_tp_size            | 8                                                                                                                        |
| decode_tp_size             | 8                                                                                                                        |
| pd_enabled                 | False                                                                                                                    |
| pd_role_layout             |                                                                                                                          |
| transport_mode             | socket_vs_myelon_process_runner                                                                                          |
| build_features             | cuda,myelon,nccl                                                                                                         |
| effective_device_ids       |                                                                                                                          |
| myelon_rpc_depth           | 8192                                                                                                                     |
| myelon_response_depth      | 8192                                                                                                                     |
| myelon_busy_spin           | True                                                                                                                     |
| prefix_cache_enabled       |                                                                                                                          |
| prefix_cache_max_tokens    |                                                                                                                          |
| kv_fraction                |                                                                                                                          |
| cpu_mem_fold               |                                                                                                                          |
| transport_settings_profile | socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off                                                    |
| run_class                  | quickpass                                                                                                                |
| result_boundary            | benchmark_complete                                                                                                       |
| artifact_class             | quickpass/benchmark_complete/full_completion                                                                             |
| stop_point                 | full_completion                                                                                                          |
| status                     | completed                                                                                                                |
| expected_case_count        |                                                                                                                          |
| observed_case_count        | 2                                                                                                                        |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_3b_tp8_cli_prefill_long_v1/report.json |

## Case Summary

|   benchmark_exit_code | case_status   |   decode_seconds_mean |   decode_tps_mean | execution_variant   |   first_prefill_seconds_mean |   first_prefill_tps_mean | label   | latency_ms_mean   |   prompt_seconds_mean |   prompt_tps_mean | requests_per_sec   | result_boundary    | runtime_sec   | skip_reason   | stop_point      | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|---------------|-----------------------|-------------------|---------------------|------------------------------|--------------------------|---------|-------------------|-----------------------|-------------------|--------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     |               1.84667 |           8868.7  | runner              |                      9.10333 |                  87.5167 | runner  |                   |               9.10333 |           22376.6 |                    | benchmark_complete |               |               | full_completion |                |                |
|                     0 | completed     |               1.91    |           8575.01 | myelon              |                      9.34667 |                  85.19   | myelon  |                   |               9.34667 |           21780.9 |                    | benchmark_complete |               |               | full_completion |                |                |
