# Benchmark Summary

| Key                     | Value                                                                                                                        |
|-------------------------|------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | server_prefill_stress                                                                                                        |
| benchmark_submode       | fixed_prompt_burst                                                                                                           |
| workload_class          | synthetic_server_fixed_prompt_burst                                                                                          |
| warmup_policy           | measure_first_turn                                                                                                           |
| first_turn_measured     | True                                                                                                                         |
| arrival_pattern         | saturation_zero_gap                                                                                                          |
| cache_pressure_profile  | relaxed                                                                                                                      |
| equivalence_group       | fixed_prompt_burst_bridge                                                                                                    |
| conversation_sampling   | round_robin                                                                                                                  |
| limit_min_tokens        | 1                                                                                                                            |
| limit_max_tokens        | 1                                                                                                                            |
| topology_overlay        | tp2                                                                                                                          |
| transport_mode          | socket_vs_myelon_process_runner                                                                                              |
| build_features          | cuda,myelon,nccl                                                                                                             |
| effective_device_ids    | [0, 1]                                                                                                                       |
| myelon_rpc_depth        |                                                                                                                              |
| myelon_response_depth   |                                                                                                                              |
| myelon_busy_spin        |                                                                                                                              |
| prefix_cache_enabled    | False                                                                                                                        |
| prefix_cache_max_tokens |                                                                                                                              |
| kv_fraction             | 0.55                                                                                                                         |
| cpu_mem_fold            | 0.5                                                                                                                          |
| run_class               | fullpass                                                                                                                     |
| result_boundary         | runtime_limited                                                                                                              |
| stop_point              | full_completion                                                                                                              |
| status                  | partial                                                                                                                      |
| expected_case_count     |                                                                                                                              |
| observed_case_count     | 1                                                                                                                            |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt/report.json |

## Case Summary

| benchmark_exit_code   | case_status            | execution_variant   | label   | latency_ms_mean   | requests_per_sec   | result_boundary   | runtime_sec   | skip_reason   | stop_point             | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|------------------------|---------------------|---------|-------------------|--------------------|-------------------|---------------|---------------|------------------------|----------------|----------------|
|                       | runtime_error_boundary | runner              | runner  |                   |                    | runtime_limited   |               |               | runtime_error_boundary |                |                |
