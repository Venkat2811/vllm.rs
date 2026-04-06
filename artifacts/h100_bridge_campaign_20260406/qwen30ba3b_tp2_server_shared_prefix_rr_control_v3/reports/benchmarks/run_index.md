# Run Index

| Key                    | Value                                                                                                                                       |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family       | server_prefill_stress                                                                                                                       |
| benchmark_submode      | shared_prefix_round_robin_control                                                                                                           |
| workload_class         | synthetic_server_shared_prefix_control                                                                                                      |
| warmup_policy          | measure_first_turn                                                                                                                          |
| first_turn_measured    | True                                                                                                                                        |
| arrival_pattern        | saturation_zero_gap                                                                                                                         |
| cache_pressure_profile | bounded_prefix                                                                                                                              |
| equivalence_group      |                                                                                                                                             |
| conversation_sampling  | round_robin                                                                                                                                 |
| limit_min_tokens       | 8                                                                                                                                           |
| limit_max_tokens       | 8                                                                                                                                           |
| topology_overlay       | tp2                                                                                                                                         |
| transport_mode         | socket_vs_myelon_process_runner                                                                                                             |
| run_class              | fullpass                                                                                                                                    |
| status                 | completed                                                                                                                                   |
| expected_case_count    | 2                                                                                                                                           |
| observed_case_count    | 2                                                                                                                                           |
| stop_point             | full_completion                                                                                                                             |
| skip_reason            |                                                                                                                                             |
| transport_supported    |                                                                                                                                             |
| transport_skip_reason  |                                                                                                                                             |
| host                   | hazy-instance-completes-fin-02                                                                                                              |
| gpu_names              | NVIDIA H100 80GB HBM3,NVIDIA H100 80GB HBM3                                                                                                 |
| model_label            | Qwen/Qwen3-30B-A3B                                                                                                                          |
| model_architecture     | Qwen3MoeForCausalLM                                                                                                                         |
| pd_supported           | True                                                                                                                                        |
| report_json            | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v3/report.json |
