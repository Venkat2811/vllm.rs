# Run Index

| Key                     | Value                                                                                                                             |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | server_prefill_stress                                                                                                             |
| benchmark_submode       | fixed_prompt_burst                                                                                                                |
| workload_class          | synthetic_server_fixed_prompt_burst                                                                                               |
| warmup_policy           | measure_first_turn                                                                                                                |
| first_turn_measured     | True                                                                                                                              |
| arrival_pattern         | saturation_zero_gap                                                                                                               |
| cache_pressure_profile  | relaxed                                                                                                                           |
| equivalence_group       | fixed_prompt_burst_bridge                                                                                                         |
| conversation_sampling   | round_robin                                                                                                                       |
| limit_min_tokens        | 1                                                                                                                                 |
| limit_max_tokens        | 1                                                                                                                                 |
| topology_overlay        | tp2                                                                                                                               |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                   |
| build_features          | cuda,myelon,nccl                                                                                                                  |
| effective_device_ids    | [0, 1]                                                                                                                            |
| myelon_rpc_depth        |                                                                                                                                   |
| myelon_response_depth   |                                                                                                                                   |
| myelon_busy_spin        |                                                                                                                                   |
| prefix_cache_enabled    | False                                                                                                                             |
| prefix_cache_max_tokens |                                                                                                                                   |
| kv_fraction             |                                                                                                                                   |
| cpu_mem_fold            | 0.5                                                                                                                               |
| run_class               | fullpass                                                                                                                          |
| status                  | completed                                                                                                                         |
| result_boundary         | benchmark_complete                                                                                                                |
| expected_case_count     |                                                                                                                                   |
| observed_case_count     | 2                                                                                                                                 |
| stop_point              | full_completion                                                                                                                   |
| skip_reason             |                                                                                                                                   |
| transport_supported     |                                                                                                                                   |
| transport_skip_reason   |                                                                                                                                   |
| host                    | plain-bear-unfolds-fin-02                                                                                                         |
| gpu_names               | NVIDIA H100 80GB HBM3,NVIDIA H100 80GB HBM3                                                                                       |
| model_label             | Qwen/Qwen3-30B-A3B                                                                                                                |
| model_architecture      | Qwen3MoeForCausalLM                                                                                                               |
| pd_supported            | True                                                                                                                              |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256/report.json |
