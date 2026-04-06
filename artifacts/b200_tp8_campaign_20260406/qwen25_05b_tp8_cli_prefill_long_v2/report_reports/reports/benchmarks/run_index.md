# Run Index

| Key                                | Value                                                                                                                     |
|------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| benchmark_family                   | prefill_stress                                                                                                            |
| benchmark_submode                  | fixed_prompt_burst                                                                                                        |
| workload_class                     | synthetic_prompt_long_stress_burst                                                                                        |
| warmup_policy                      | cli_warmup_runs:1                                                                                                         |
| first_turn_measured                | True                                                                                                                      |
| arrival_pattern                    | prompt_burst_serial_runs                                                                                                  |
| cache_pressure_profile             | unspecified                                                                                                               |
| equivalence_group                  |                                                                                                                           |
| conversation_sampling              |                                                                                                                           |
| limit_min_tokens                   |                                                                                                                           |
| limit_max_tokens                   |                                                                                                                           |
| topology_overlay                   | tp8                                                                                                                       |
| tp_scale_overlay                   | tp8                                                                                                                       |
| prefill_tp_size                    | 8                                                                                                                         |
| decode_tp_size                     | 8                                                                                                                         |
| pd_enabled                         | False                                                                                                                     |
| pd_role_layout                     |                                                                                                                           |
| transport_mode                     | socket_vs_myelon_process_runner                                                                                           |
| build_features                     |                                                                                                                           |
| effective_device_ids               |                                                                                                                           |
| myelon_rpc_depth                   |                                                                                                                           |
| myelon_response_depth              |                                                                                                                           |
| myelon_busy_spin                   |                                                                                                                           |
| prefix_cache_enabled               |                                                                                                                           |
| prefix_cache_max_tokens            |                                                                                                                           |
| kv_fraction                        |                                                                                                                           |
| cpu_mem_fold                       |                                                                                                                           |
| transport_settings_profile         | socket_vs_myelon_process_runner/prefix_off                                                                                |
| run_class                          | quickpass                                                                                                                 |
| status                             | warmup_incomplete_metrics                                                                                                 |
| result_boundary                    | benchmark_complete                                                                                                        |
| artifact_class                     | quickpass/benchmark_complete/warmup_incomplete_metrics                                                                    |
| expected_case_count                |                                                                                                                           |
| observed_case_count                | 0                                                                                                                         |
| stop_point                         | warmup_incomplete_metrics                                                                                                 |
| skip_reason                        |                                                                                                                           |
| pressure_profile_outcome_pair      |                                                                                                                           |
| observed_cache_pressure_level_pair |                                                                                                                           |
| transport_supported                |                                                                                                                           |
| transport_skip_reason              |                                                                                                                           |
| host                               | weak-time-laughs-fin-03                                                                                                   |
| gpu_names                          | NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200                           |
| model_label                        | Qwen/Qwen2.5-0.5B-Instruct                                                                                                |
| model_architecture                 | Qwen2ForCausalLM                                                                                                          |
| pd_supported                       | True                                                                                                                      |
| report_json                        | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_05b_tp8_cli_prefill_long_v2/report.json |
