# Benchmark Summary

| Key                        | Value                                                                                                                                 |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | prefill_stress                                                                                                                        |
| benchmark_submode          | fixed_prompt_burst                                                                                                                    |
| workload_class             | synthetic_prompt_long_stress_burst                                                                                                    |
| warmup_policy              | cli_warmup_runs:1                                                                                                                     |
| first_turn_measured        | True                                                                                                                                  |
| arrival_pattern            | prompt_burst_serial_runs                                                                                                              |
| cache_pressure_profile     | unspecified                                                                                                                           |
| equivalence_group          |                                                                                                                                       |
| conversation_sampling      |                                                                                                                                       |
| limit_min_tokens           |                                                                                                                                       |
| limit_max_tokens           |                                                                                                                                       |
| topology_overlay           | tp8                                                                                                                                   |
| tp_scale_overlay           | tp8                                                                                                                                   |
| prefill_tp_size            | 8                                                                                                                                     |
| decode_tp_size             | 8                                                                                                                                     |
| pd_enabled                 | False                                                                                                                                 |
| pd_role_layout             |                                                                                                                                       |
| transport_mode             | socket_vs_myelon_process_runner                                                                                                       |
| build_features             | cuda,myelon,nccl                                                                                                                      |
| effective_device_ids       |                                                                                                                                       |
| myelon_rpc_depth           | 8192                                                                                                                                  |
| myelon_response_depth      | 8192                                                                                                                                  |
| myelon_busy_spin           | True                                                                                                                                  |
| prefix_cache_enabled       |                                                                                                                                       |
| prefix_cache_max_tokens    |                                                                                                                                       |
| kv_fraction                |                                                                                                                                       |
| cpu_mem_fold               |                                                                                                                                       |
| transport_settings_profile | socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off                                                                 |
| run_class                  | quickpass                                                                                                                             |
| result_boundary            | stop_point_limited                                                                                                                    |
| artifact_class             | quickpass/stop_point_limited/first_prefill_completion                                                                                 |
| stop_point                 | first_prefill_completion                                                                                                              |
| status                     | completed                                                                                                                             |
| expected_case_count        |                                                                                                                                       |
| observed_case_count        | 2                                                                                                                                     |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_72b_tp8_cli_prefill_firstprefill_b64_v3/report.json |

## Case Summary

|   benchmark_exit_code | case_status              | decode_seconds_mean   | decode_tps_mean   | execution_variant   |   first_prefill_seconds_mean |   first_prefill_tps_mean | label   | latency_ms_mean   |   prompt_seconds_mean |   prompt_tps_mean | requests_per_sec   | result_boundary    | runtime_sec   | skip_reason   | stop_point               | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|--------------------------|-----------------------|-------------------|---------------------|------------------------------|--------------------------|---------|-------------------|-----------------------|-------------------|--------------------|--------------------|---------------|---------------|--------------------------|----------------|----------------|
|                     0 | first_prefill_completion |                       |                   | runner              |                         18.2 |                    43.73 | runner  |                   |                  18.2 |             43.73 |                    | stop_point_limited |               |               | first_prefill_completion |                |                |
|                     0 | first_prefill_completion |                       |                   | myelon              |                         17.9 |                    44.48 | myelon  |                   |                  17.9 |             44.48 |                    | stop_point_limited |               |               | first_prefill_completion |                |                |
