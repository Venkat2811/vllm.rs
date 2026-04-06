# Benchmark Summary

| Key                    | Value                                                                                                                        |
|------------------------|------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family       | server_prefill_stress                                                                                                        |
| benchmark_submode      | fixed_prompt_burst                                                                                                           |
| workload_class         | synthetic_server_fixed_prompt_burst                                                                                          |
| warmup_policy          | measure_first_turn                                                                                                           |
| first_turn_measured    | True                                                                                                                         |
| arrival_pattern        | saturation_zero_gap                                                                                                          |
| cache_pressure_profile | relaxed                                                                                                                      |
| equivalence_group      | fixed_prompt_burst_bridge                                                                                                    |
| conversation_sampling  | round_robin                                                                                                                  |
| limit_min_tokens       | 1                                                                                                                            |
| limit_max_tokens       | 1                                                                                                                            |
| topology_overlay       | tp2                                                                                                                          |
| transport_mode         | socket_vs_myelon_process_runner                                                                                              |
| run_class              | fullpass                                                                                                                     |
| stop_point             | full_completion                                                                                                              |
| status                 | partial                                                                                                                      |
| report_json            | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt/report.json |

## Case Summary

| benchmark_exit_code   | case_status            | execution_variant   | label   | skip_reason   | stop_point             |
|-----------------------|------------------------|---------------------|---------|---------------|------------------------|
|                       | runtime_error_boundary | runner              | runner  |               | runtime_error_boundary |
