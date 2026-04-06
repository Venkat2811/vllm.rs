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
| transport_mode          | socket_vs_myelon_process_runner                                                                                                  |
| build_features          | cuda,myelon,nccl                                                                                                                 |
| effective_device_ids    |                                                                                                                                  |
| myelon_rpc_depth        | 8192                                                                                                                             |
| myelon_response_depth   | 8192                                                                                                                             |
| myelon_busy_spin        | True                                                                                                                             |
| prefix_cache_enabled    |                                                                                                                                  |
| prefix_cache_max_tokens |                                                                                                                                  |
| kv_fraction             |                                                                                                                                  |
| cpu_mem_fold            |                                                                                                                                  |
| run_class               | fullpass                                                                                                                         |
| status                  | completed                                                                                                                        |
| result_boundary         | stop_point_limited                                                                                                               |
| expected_case_count     |                                                                                                                                  |
| observed_case_count     | 2                                                                                                                                |
| stop_point              | minimal_decode_completion                                                                                                        |
| skip_reason             |                                                                                                                                  |
| transport_supported     |                                                                                                                                  |
| transport_skip_reason   |                                                                                                                                  |
| host                    | hazy-instance-completes-fin-02                                                                                                   |
| gpu_names               | NVIDIA H100 80GB HBM3,NVIDIA H100 80GB HBM3                                                                                      |
| model_label             | Qwen/Qwen3-30B-A3B                                                                                                               |
| model_architecture      | Qwen3MoeForCausalLM                                                                                                              |
| pd_supported            | True                                                                                                                             |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch128_v1/report.json |
