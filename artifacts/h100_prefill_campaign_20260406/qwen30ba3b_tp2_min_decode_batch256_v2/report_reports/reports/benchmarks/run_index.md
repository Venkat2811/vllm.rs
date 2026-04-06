# Run Index

| Key                     | Value                                                                                                                            |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | prefill_stress                                                                                                                   |
| benchmark_submode       | fixed_prompt_burst                                                                                                               |
| workload_class          | custom_prompt_env_burst                                                                                                          |
| warmup_policy           | cli_warmup_runs:1                                                                                                                |
| first_turn_measured     | True                                                                                                                             |
| arrival_pattern         | prompt_burst_serial_runs                                                                                                         |
| cache_pressure_profile  | unspecified                                                                                                                      |
| equivalence_group       |                                                                                                                                  |
| conversation_sampling   |                                                                                                                                  |
| limit_min_tokens        |                                                                                                                                  |
| limit_max_tokens        |                                                                                                                                  |
| topology_overlay        | tp2                                                                                                                              |
| tp_scale_overlay        | tp2                                                                                                                              |
| prefill_tp_size         | 2                                                                                                                                |
| decode_tp_size          | 2                                                                                                                                |
| pd_enabled              | False                                                                                                                            |
| pd_role_layout          |                                                                                                                                  |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                  |
| build_features          |                                                                                                                                  |
| effective_device_ids    |                                                                                                                                  |
| myelon_rpc_depth        |                                                                                                                                  |
| myelon_response_depth   |                                                                                                                                  |
| myelon_busy_spin        |                                                                                                                                  |
| prefix_cache_enabled    |                                                                                                                                  |
| prefix_cache_max_tokens |                                                                                                                                  |
| kv_fraction             |                                                                                                                                  |
| cpu_mem_fold            |                                                                                                                                  |
| run_class               | fullpass                                                                                                                         |
| status                  | warmup_incomplete_metrics                                                                                                        |
| result_boundary         | benchmark_complete                                                                                                               |
| expected_case_count     |                                                                                                                                  |
| observed_case_count     | 0                                                                                                                                |
| stop_point              | warmup_incomplete_metrics                                                                                                        |
| skip_reason             |                                                                                                                                  |
| transport_supported     |                                                                                                                                  |
| transport_skip_reason   |                                                                                                                                  |
| host                    | hazy-instance-completes-fin-02                                                                                                   |
| gpu_names               | NVIDIA H100 80GB HBM3,NVIDIA H100 80GB HBM3                                                                                      |
| model_label             | Qwen/Qwen3-30B-A3B                                                                                                               |
| model_architecture      | Qwen3MoeForCausalLM                                                                                                              |
| pd_supported            | True                                                                                                                             |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch256_v2/report.json |
