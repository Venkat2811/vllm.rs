# Run Index

| Key                                | Value                                                                                                                                      |
|------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family                   | server_prefill_stress                                                                                                                      |
| benchmark_submode                  | fixed_prompt_burst                                                                                                                         |
| workload_class                     | synthetic_server_fixed_prompt_burst                                                                                                        |
| warmup_policy                      | measure_first_turn                                                                                                                         |
| first_turn_measured                | True                                                                                                                                       |
| arrival_pattern                    | saturation_zero_gap                                                                                                                        |
| cache_pressure_profile             | relaxed                                                                                                                                    |
| equivalence_group                  | fixed_prompt_burst_bridge                                                                                                                  |
| conversation_sampling              | round_robin                                                                                                                                |
| limit_min_tokens                   | 1                                                                                                                                          |
| limit_max_tokens                   | 1                                                                                                                                          |
| topology_overlay                   | tp2                                                                                                                                        |
| tp_scale_overlay                   | tp2                                                                                                                                        |
| prefill_tp_size                    | 2                                                                                                                                          |
| decode_tp_size                     | 2                                                                                                                                          |
| pd_enabled                         | False                                                                                                                                      |
| pd_role_layout                     |                                                                                                                                            |
| transport_mode                     | socket_vs_myelon_process_runner                                                                                                            |
| build_features                     | cuda,myelon,nccl                                                                                                                           |
| effective_device_ids               | [0, 1]                                                                                                                                     |
| myelon_rpc_depth                   | 8192                                                                                                                                       |
| myelon_response_depth              | 8192                                                                                                                                       |
| myelon_busy_spin                   | True                                                                                                                                       |
| prefix_cache_enabled               | False                                                                                                                                      |
| prefix_cache_max_tokens            |                                                                                                                                            |
| kv_fraction                        |                                                                                                                                            |
| cpu_mem_fold                       | 0.5                                                                                                                                        |
| transport_settings_profile         | socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/cpufold0.5                                                           |
| run_class                          | fullpass                                                                                                                                   |
| status                             | partial                                                                                                                                    |
| result_boundary                    | benchmark_complete                                                                                                                         |
| artifact_class                     | fullpass/benchmark_complete/full_completion                                                                                                |
| expected_case_count                | 2                                                                                                                                          |
| observed_case_count                | 1                                                                                                                                          |
| stop_point                         | full_completion                                                                                                                            |
| skip_reason                        |                                                                                                                                            |
| pressure_profile_outcome_pair      | requested_relaxed_observed -> none                                                                                                         |
| observed_cache_pressure_level_pair | no_observed_pressure -> none                                                                                                               |
| transport_supported                |                                                                                                                                            |
| transport_skip_reason              |                                                                                                                                            |
| host                               | loud-rain-thinks-fin-03                                                                                                                    |
| gpu_names                          | NVIDIA H200,NVIDIA H200,NVIDIA H200,NVIDIA H200                                                                                            |
| model_label                        | Qwen/Qwen3-30B-A3B                                                                                                                         |
| model_architecture                 | Qwen3MoeForCausalLM                                                                                                                        |
| pd_supported                       | True                                                                                                                                       |
| report_json                        | /root/Documents/myelon-launch/vllm.rs/artifacts/h200_external_python_phase_a_20260407/qwen30ba3b_tp2_random_1024_1_nostream_c1/report.json |
