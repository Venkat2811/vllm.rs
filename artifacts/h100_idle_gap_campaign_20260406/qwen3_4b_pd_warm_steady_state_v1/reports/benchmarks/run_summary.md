# Benchmark Summary

| Key                        | Value                                                                                                                        |
|----------------------------|------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | pd_qos                                                                                                                       |
| benchmark_submode          | warm_steady_state                                                                                                            |
| workload_class             | synthetic_multi_turn                                                                                                         |
| warmup_policy              | warmup_step_skips_first_turn                                                                                                 |
| first_turn_measured        | False                                                                                                                        |
| arrival_pattern            | saturation_zero_gap                                                                                                          |
| cache_pressure_profile     | unspecified                                                                                                                  |
| equivalence_group          |                                                                                                                              |
| conversation_sampling      |                                                                                                                              |
| limit_min_tokens           |                                                                                                                              |
| limit_max_tokens           |                                                                                                                              |
| topology_overlay           | pd_tp1                                                                                                                       |
| tp_scale_overlay           | pd(tp1/tp1)                                                                                                                  |
| prefill_tp_size            | 1                                                                                                                            |
| decode_tp_size             | 1                                                                                                                            |
| pd_enabled                 | True                                                                                                                         |
| pd_role_layout             | same_host_split_roles                                                                                                        |
| transport_mode             | pd_tcp                                                                                                                       |
| build_features             | cuda,myelon,nccl                                                                                                             |
| effective_device_ids       |                                                                                                                              |
| myelon_rpc_depth           | 8192                                                                                                                         |
| myelon_response_depth      | 8192                                                                                                                         |
| myelon_busy_spin           | True                                                                                                                         |
| prefix_cache_enabled       |                                                                                                                              |
| prefix_cache_max_tokens    |                                                                                                                              |
| kv_fraction                |                                                                                                                              |
| cpu_mem_fold               |                                                                                                                              |
| transport_settings_profile | pd_tcp/rpc8192/resp8192/busy_spin/prefix_off                                                                                 |
| run_class                  | fullpass                                                                                                                     |
| result_boundary            | benchmark_complete                                                                                                           |
| artifact_class             | fullpass/benchmark_complete/full_completion                                                                                  |
| stop_point                 | full_completion                                                                                                              |
| status                     | completed                                                                                                                    |
| expected_case_count        | 2                                                                                                                            |
| observed_case_count        | 2                                                                                                                            |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label     |   latency_ms_mean |   observed_client_done_count |   observed_client_no_more_work_count |   observed_client_termination_signal_count |   observed_clients_with_failures |   observed_failed_requests_total |   observed_http_422_rejection_count | observed_request_rejections   |   observed_successful_requests_total |   requests_per_sec | result_boundary    |   runtime_sec | skip_reason   | stop_point      |   tpot_ms_mean |   ttft_ms_mean |
|-----------------------|---------------|---------------------|-----------|-------------------|------------------------------|--------------------------------------|--------------------------------------------|----------------------------------|----------------------------------|-------------------------------------|-------------------------------|--------------------------------------|--------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner_pd           | runner_pd |           497.185 |                            2 |                                    2 |                                          0 |                                0 |                                0 |                                   0 | False                         |                                   14 |              3.163 | benchmark_complete |         1.897 |               | full_completion |          6.907 |        257.375 |
|                     0 | completed     | myelon_pd           | myelon_pd |           501.132 |                            2 |                                    2 |                                          0 |                                0 |                                0 |                                   0 | False                         |                                   14 |              3.215 | benchmark_complete |         1.866 |               | full_completion |          6.774 |        265.975 |
