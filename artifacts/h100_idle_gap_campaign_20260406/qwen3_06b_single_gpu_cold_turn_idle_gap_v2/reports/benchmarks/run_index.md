# Run Index

| Key                     | Value                                                                                                                                  |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | serving_qos                                                                                                                            |
| benchmark_submode       | cold_turn_idle_gap                                                                                                                     |
| workload_class          | synthetic_multi_turn                                                                                                                   |
| warmup_policy           | measure_first_turn                                                                                                                     |
| first_turn_measured     | True                                                                                                                                   |
| arrival_pattern         | configured_fixed_rate                                                                                                                  |
| cache_pressure_profile  | relaxed                                                                                                                                |
| equivalence_group       |                                                                                                                                        |
| conversation_sampling   | round_robin                                                                                                                            |
| limit_min_tokens        |                                                                                                                                        |
| limit_max_tokens        |                                                                                                                                        |
| topology_overlay        | single_gpu                                                                                                                             |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                        |
| build_features          | cuda,myelon,nccl                                                                                                                       |
| effective_device_ids    |                                                                                                                                        |
| myelon_rpc_depth        | 8192                                                                                                                                   |
| myelon_response_depth   | 8192                                                                                                                                   |
| myelon_busy_spin        | False                                                                                                                                  |
| prefix_cache_enabled    | False                                                                                                                                  |
| prefix_cache_max_tokens |                                                                                                                                        |
| kv_fraction             |                                                                                                                                        |
| cpu_mem_fold            |                                                                                                                                        |
| run_class               | fullpass                                                                                                                               |
| status                  | completed                                                                                                                              |
| expected_case_count     | 2                                                                                                                                      |
| observed_case_count     | 2                                                                                                                                      |
| stop_point              | full_completion                                                                                                                        |
| skip_reason             |                                                                                                                                        |
| transport_supported     |                                                                                                                                        |
| transport_skip_reason   |                                                                                                                                        |
| host                    | hazy-instance-completes-fin-02                                                                                                         |
| gpu_names               | NVIDIA H100 80GB HBM3,NVIDIA H100 80GB HBM3                                                                                            |
| model_label             | Qwen/Qwen3-0.6B                                                                                                                        |
| model_architecture      | Qwen3ForCausalLM                                                                                                                       |
| pd_supported            | True                                                                                                                                   |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/report.json |
