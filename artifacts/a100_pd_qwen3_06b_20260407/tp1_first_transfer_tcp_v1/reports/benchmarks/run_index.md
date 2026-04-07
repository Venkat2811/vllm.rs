# Run Index

| Key                                | Value                                                                                                            |
|------------------------------------|------------------------------------------------------------------------------------------------------------------|
| benchmark_family                   | pd_qos                                                                                                           |
| benchmark_submode                  | first_transfer_control                                                                                           |
| workload_class                     | pd_first_transfer_control                                                                                        |
| warmup_policy                      | measure_first_turn                                                                                               |
| first_turn_measured                | True                                                                                                             |
| arrival_pattern                    | saturation_zero_gap                                                                                              |
| cache_pressure_profile             | unspecified                                                                                                      |
| equivalence_group                  |                                                                                                                  |
| conversation_sampling              |                                                                                                                  |
| limit_min_tokens                   |                                                                                                                  |
| limit_max_tokens                   |                                                                                                                  |
| topology_overlay                   | pd_tp1                                                                                                           |
| tp_scale_overlay                   | pd(tp1/tp1)                                                                                                      |
| prefill_tp_size                    | 1                                                                                                                |
| decode_tp_size                     | 1                                                                                                                |
| pd_enabled                         | True                                                                                                             |
| pd_role_layout                     | same_host_split_roles                                                                                            |
| transport_mode                     | pd_tcp                                                                                                           |
| build_features                     | cuda,myelon,nccl                                                                                                 |
| effective_device_ids               |                                                                                                                  |
| myelon_rpc_depth                   | 8192                                                                                                             |
| myelon_response_depth              | 8192                                                                                                             |
| myelon_busy_spin                   | True                                                                                                             |
| prefix_cache_enabled               |                                                                                                                  |
| prefix_cache_max_tokens            |                                                                                                                  |
| kv_fraction                        |                                                                                                                  |
| cpu_mem_fold                       |                                                                                                                  |
| transport_settings_profile         | pd_tcp/rpc8192/resp8192/busy_spin/prefix_off                                                                     |
| run_class                          | quickpass                                                                                                        |
| status                             | partial                                                                                                          |
| result_boundary                    | benchmark_failed                                                                                                 |
| artifact_class                     | quickpass/benchmark_failed/full_completion                                                                       |
| expected_case_count                | 2                                                                                                                |
| observed_case_count                | 2                                                                                                                |
| stop_point                         | full_completion                                                                                                  |
| skip_reason                        |                                                                                                                  |
| pressure_profile_outcome_pair      |                                                                                                                  |
| observed_cache_pressure_level_pair |                                                                                                                  |
| transport_supported                | True                                                                                                             |
| transport_skip_reason              |                                                                                                                  |
| host                               | dark-heart-passes-fin-03                                                                                         |
| gpu_names                          | NVIDIA A100-SXM4-80GB,NVIDIA A100-SXM4-80GB,NVIDIA A100-SXM4-80GB,NVIDIA A100-SXM4-80GB                          |
| model_label                        | Qwen/Qwen3-0.6B                                                                                                  |
| model_architecture                 | Qwen3ForCausalLM                                                                                                 |
| pd_supported                       | True                                                                                                             |
| report_json                        | /root/Documents/myelon-launch/vllm.rs/artifacts/a100_pd_qwen3_06b_20260407/tp1_first_transfer_tcp_v1/report.json |
