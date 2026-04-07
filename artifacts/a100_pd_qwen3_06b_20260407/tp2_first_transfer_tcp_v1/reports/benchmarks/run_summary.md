# Benchmark Summary

| Key                        | Value                                                                                                            |
|----------------------------|------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | pd_qos                                                                                                           |
| benchmark_submode          | first_transfer_control                                                                                           |
| workload_class             | pd_first_transfer_control                                                                                        |
| warmup_policy              | measure_first_turn                                                                                               |
| first_turn_measured        | True                                                                                                             |
| arrival_pattern            | saturation_zero_gap                                                                                              |
| cache_pressure_profile     | unspecified                                                                                                      |
| equivalence_group          |                                                                                                                  |
| conversation_sampling      |                                                                                                                  |
| limit_min_tokens           |                                                                                                                  |
| limit_max_tokens           |                                                                                                                  |
| topology_overlay           | pd_tp2                                                                                                           |
| tp_scale_overlay           | pd(tp2/tp2)                                                                                                      |
| prefill_tp_size            | 2                                                                                                                |
| decode_tp_size             | 2                                                                                                                |
| pd_enabled                 | True                                                                                                             |
| pd_role_layout             | same_host_split_roles                                                                                            |
| transport_mode             | pd_tcp                                                                                                           |
| build_features             | cuda,myelon,nccl                                                                                                 |
| effective_device_ids       |                                                                                                                  |
| myelon_rpc_depth           | 8192                                                                                                             |
| myelon_response_depth      | 8192                                                                                                             |
| myelon_busy_spin           | True                                                                                                             |
| prefix_cache_enabled       |                                                                                                                  |
| prefix_cache_max_tokens    |                                                                                                                  |
| kv_fraction                |                                                                                                                  |
| cpu_mem_fold               |                                                                                                                  |
| transport_settings_profile | pd_tcp/rpc8192/resp8192/busy_spin/prefix_off                                                                     |
| run_class                  | quickpass                                                                                                        |
| result_boundary            | benchmark_complete                                                                                               |
| artifact_class             | quickpass/benchmark_complete/full_completion                                                                     |
| stop_point                 | full_completion                                                                                                  |
| status                     | completed                                                                                                        |
| expected_case_count        | 2                                                                                                                |
| observed_case_count        | 2                                                                                                                |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/a100_pd_qwen3_06b_20260407/tp2_first_transfer_tcp_v1/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label     | latency_ms_mean   |   observed_client_done_count |   observed_client_no_more_work_count |   observed_client_termination_signal_count |   observed_clients_with_failures |   observed_failed_requests_total |   observed_http_422_rejection_count | observed_request_rejections   |   observed_successful_requests_total |   requests_per_sec | result_boundary    |   runtime_sec | skip_reason   | stop_point      | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|---------------|---------------------|-----------|-------------------|------------------------------|--------------------------------------|--------------------------------------------|----------------------------------|----------------------------------|-------------------------------------|-------------------------------|--------------------------------------|--------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner_pd           | runner_pd |                   |                            1 |                                    1 |                                          0 |                                0 |                                0 |                                   0 | False                         |                                    1 |              0.566 | benchmark_complete |         1.768 |               | full_completion |                |                |
|                     0 | completed     | myelon_pd           | myelon_pd |                   |                            1 |                                    1 |                                          0 |                                0 |                                0 |                                   0 | False                         |                                    1 |              0.175 | benchmark_complete |         5.699 |               | full_completion |                |                |
