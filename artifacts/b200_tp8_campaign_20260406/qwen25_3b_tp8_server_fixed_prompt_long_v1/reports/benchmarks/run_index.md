# Run Index

| Key                                | Value                                                                                                                            |
|------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family                   | server_prefill_stress                                                                                                            |
| benchmark_submode                  | fixed_prompt_burst                                                                                                               |
| workload_class                     | synthetic_server_fixed_prompt_burst                                                                                              |
| warmup_policy                      | measure_first_turn                                                                                                               |
| first_turn_measured                | True                                                                                                                             |
| arrival_pattern                    | saturation_zero_gap                                                                                                              |
| cache_pressure_profile             | relaxed                                                                                                                          |
| equivalence_group                  | fixed_prompt_burst_bridge                                                                                                        |
| conversation_sampling              | round_robin                                                                                                                      |
| limit_min_tokens                   | 1                                                                                                                                |
| limit_max_tokens                   | 1                                                                                                                                |
| topology_overlay                   | tp8                                                                                                                              |
| tp_scale_overlay                   | tp8                                                                                                                              |
| prefill_tp_size                    | 8                                                                                                                                |
| decode_tp_size                     | 8                                                                                                                                |
| pd_enabled                         | False                                                                                                                            |
| pd_role_layout                     |                                                                                                                                  |
| transport_mode                     | socket_vs_myelon_process_runner                                                                                                  |
| build_features                     | cuda,myelon,nccl                                                                                                                 |
| effective_device_ids               | [0, 1, 2, 3, 4, 5, 6, 7]                                                                                                         |
| myelon_rpc_depth                   | 8192                                                                                                                             |
| myelon_response_depth              | 8192                                                                                                                             |
| myelon_busy_spin                   | True                                                                                                                             |
| prefix_cache_enabled               | False                                                                                                                            |
| prefix_cache_max_tokens            |                                                                                                                                  |
| kv_fraction                        |                                                                                                                                  |
| cpu_mem_fold                       | 0.5                                                                                                                              |
| transport_settings_profile         | socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/cpufold0.5                                                 |
| run_class                          | fullpass                                                                                                                         |
| status                             | partial                                                                                                                          |
| result_boundary                    | benchmark_failed                                                                                                                 |
| artifact_class                     | fullpass/benchmark_failed/full_completion                                                                                        |
| expected_case_count                | 2                                                                                                                                |
| observed_case_count                | 2                                                                                                                                |
| stop_point                         | full_completion                                                                                                                  |
| skip_reason                        |                                                                                                                                  |
| pressure_profile_outcome_pair      |                                                                                                                                  |
| observed_cache_pressure_level_pair |                                                                                                                                  |
| transport_supported                |                                                                                                                                  |
| transport_skip_reason              |                                                                                                                                  |
| host                               | weak-time-laughs-fin-03                                                                                                          |
| gpu_names                          | NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200,NVIDIA B200                                  |
| model_label                        | Qwen/Qwen2.5-3B-Instruct                                                                                                         |
| model_architecture                 | Qwen2ForCausalLM                                                                                                                 |
| pd_supported                       | True                                                                                                                             |
| report_json                        | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_3b_tp8_server_fixed_prompt_long_v1/report.json |
