# Run Index

| Key                     | Value                                                                                                                             |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | server_prefill_stress                                                                                                             |
| benchmark_submode       | cache_thrash_round_robin                                                                                                          |
| workload_class          | synthetic_server_prefill_stress                                                                                                   |
| warmup_policy           | measure_first_turn                                                                                                                |
| first_turn_measured     | True                                                                                                                              |
| arrival_pattern         | saturation_zero_gap                                                                                                               |
| cache_pressure_profile  | hard_thrash                                                                                                                       |
| equivalence_group       |                                                                                                                                   |
| conversation_sampling   | round_robin                                                                                                                       |
| limit_min_tokens        | 8                                                                                                                                 |
| limit_max_tokens        | 8                                                                                                                                 |
| topology_overlay        | tp2                                                                                                                               |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                   |
| build_features          | cuda,myelon,nccl                                                                                                                  |
| effective_device_ids    | [0, 1]                                                                                                                            |
| myelon_rpc_depth        | 8192                                                                                                                              |
| myelon_response_depth   | 8192                                                                                                                              |
| myelon_busy_spin        | True                                                                                                                              |
| prefix_cache_enabled    | True                                                                                                                              |
| prefix_cache_max_tokens | 1024                                                                                                                              |
| kv_fraction             | 0.08                                                                                                                              |
| cpu_mem_fold            | 0.05                                                                                                                              |
| run_class               | fullpass                                                                                                                          |
| status                  | completed                                                                                                                         |
| result_boundary         | benchmark_complete                                                                                                                |
| expected_case_count     | 2                                                                                                                                 |
| observed_case_count     | 2                                                                                                                                 |
| stop_point              | full_completion                                                                                                                   |
| skip_reason             |                                                                                                                                   |
| transport_supported     |                                                                                                                                   |
| transport_skip_reason   |                                                                                                                                   |
| host                    | hazy-instance-completes-fin-02                                                                                                    |
| gpu_names               | NVIDIA H100 80GB HBM3,NVIDIA H100 80GB HBM3                                                                                       |
| model_label             | Qwen/Qwen3-0.6B                                                                                                                   |
| model_architecture      | Qwen3ForCausalLM                                                                                                                  |
| pd_supported            | True                                                                                                                              |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_cache_thrash_rr_v1/report.json |
