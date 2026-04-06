# Run Index

| Key                                | Value                                                                                                                         |
|------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family                   | pd_qos                                                                                                                        |
| benchmark_submode                  | cold_turn_idle_gap                                                                                                            |
| workload_class                     | synthetic_multi_turn                                                                                                          |
| warmup_policy                      | measure_first_turn                                                                                                            |
| first_turn_measured                | True                                                                                                                          |
| arrival_pattern                    | configured_fixed_rate                                                                                                         |
| cache_pressure_profile             | unspecified                                                                                                                   |
| equivalence_group                  |                                                                                                                               |
| conversation_sampling              |                                                                                                                               |
| limit_min_tokens                   |                                                                                                                               |
| limit_max_tokens                   |                                                                                                                               |
| topology_overlay                   | pd_tp1                                                                                                                        |
| tp_scale_overlay                   | pd(tp1/tp1)                                                                                                                   |
| prefill_tp_size                    | 1                                                                                                                             |
| decode_tp_size                     | 1                                                                                                                             |
| pd_enabled                         | True                                                                                                                          |
| pd_role_layout                     | same_host_split_roles                                                                                                         |
| transport_mode                     | pd_tcp                                                                                                                        |
| build_features                     | cuda,myelon,nccl                                                                                                              |
| effective_device_ids               |                                                                                                                               |
| myelon_rpc_depth                   | 8192                                                                                                                          |
| myelon_response_depth              | 8192                                                                                                                          |
| myelon_busy_spin                   | True                                                                                                                          |
| prefix_cache_enabled               |                                                                                                                               |
| prefix_cache_max_tokens            |                                                                                                                               |
| kv_fraction                        |                                                                                                                               |
| cpu_mem_fold                       |                                                                                                                               |
| transport_settings_profile         | pd_tcp/rpc8192/resp8192/busy_spin/prefix_off                                                                                  |
| run_class                          | fullpass                                                                                                                      |
| status                             | completed                                                                                                                     |
| result_boundary                    | benchmark_complete                                                                                                            |
| artifact_class                     | fullpass/benchmark_complete/full_completion                                                                                   |
| expected_case_count                | 2                                                                                                                             |
| observed_case_count                | 2                                                                                                                             |
| stop_point                         | full_completion                                                                                                               |
| skip_reason                        |                                                                                                                               |
| pressure_profile_outcome_pair      |                                                                                                                               |
| observed_cache_pressure_level_pair |                                                                                                                               |
| transport_supported                | True                                                                                                                          |
| transport_skip_reason              |                                                                                                                               |
| host                               | hazy-instance-completes-fin-02                                                                                                |
| gpu_names                          | NVIDIA H100 80GB HBM3,NVIDIA H100 80GB HBM3                                                                                   |
| model_label                        | Qwen/Qwen3-4B                                                                                                                 |
| model_architecture                 | Qwen3ForCausalLM                                                                                                              |
| pd_supported                       | True                                                                                                                          |
| report_json                        | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_cold_turn_idle_gap_v1/report.json |
