# Benchmark Summary

| Key                     | Value                                                                                                                   |
|-------------------------|-------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | prefill_stress                                                                                                          |
| benchmark_submode       | fixed_prompt_burst                                                                                                      |
| workload_class          | custom_prompt_env_burst                                                                                                 |
| warmup_policy           | cli_warmup_runs:1                                                                                                       |
| first_turn_measured     | True                                                                                                                    |
| arrival_pattern         | prompt_burst_serial_runs                                                                                                |
| cache_pressure_profile  | unspecified                                                                                                             |
| equivalence_group       |                                                                                                                         |
| conversation_sampling   |                                                                                                                         |
| limit_min_tokens        |                                                                                                                         |
| limit_max_tokens        |                                                                                                                         |
| topology_overlay        | tp2                                                                                                                     |
| tp_scale_overlay        | tp2                                                                                                                     |
| prefill_tp_size         | 2                                                                                                                       |
| decode_tp_size          | 2                                                                                                                       |
| pd_enabled              | False                                                                                                                   |
| pd_role_layout          |                                                                                                                         |
| transport_mode          | socket_vs_myelon_process_runner                                                                                         |
| build_features          |                                                                                                                         |
| effective_device_ids    |                                                                                                                         |
| myelon_rpc_depth        |                                                                                                                         |
| myelon_response_depth   |                                                                                                                         |
| myelon_busy_spin        |                                                                                                                         |
| prefix_cache_enabled    |                                                                                                                         |
| prefix_cache_max_tokens |                                                                                                                         |
| kv_fraction             |                                                                                                                         |
| cpu_mem_fold            |                                                                                                                         |
| run_class               | fullpass                                                                                                                |
| result_boundary         | benchmark_complete                                                                                                      |
| stop_point              | warmup_incomplete_metrics                                                                                               |
| status                  | warmup_incomplete_metrics                                                                                               |
| expected_case_count     |                                                                                                                         |
| observed_case_count     | 0                                                                                                                       |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_v1/report.json |

## Case Summary

No case rows were available.
