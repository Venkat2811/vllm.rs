# Benchmark Summary

| Key                     | Value                                                                                                                                   |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | server_prefill_stress                                                                                                                   |
| benchmark_submode       | fixed_prompt_burst                                                                                                                      |
| workload_class          | synthetic_server_fixed_prompt_burst                                                                                                     |
| warmup_policy           | measure_first_turn                                                                                                                      |
| first_turn_measured     | True                                                                                                                                    |
| arrival_pattern         | saturation_zero_gap                                                                                                                     |
| cache_pressure_profile  | relaxed                                                                                                                                 |
| equivalence_group       | fixed_prompt_burst_bridge                                                                                                               |
| conversation_sampling   | round_robin                                                                                                                             |
| limit_min_tokens        | 1                                                                                                                                       |
| limit_max_tokens        | 1                                                                                                                                       |
| topology_overlay        | single_gpu                                                                                                                              |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                         |
| build_features          | cuda,myelon,nccl                                                                                                                        |
| effective_device_ids    | [0]                                                                                                                                     |
| myelon_rpc_depth        | 8192                                                                                                                                    |
| myelon_response_depth   | 8192                                                                                                                                    |
| myelon_busy_spin        | False                                                                                                                                   |
| prefix_cache_enabled    | False                                                                                                                                   |
| prefix_cache_max_tokens |                                                                                                                                         |
| kv_fraction             | 0.55                                                                                                                                    |
| cpu_mem_fold            | 0.5                                                                                                                                     |
| run_class               | fullpass                                                                                                                                |
| stop_point              | full_completion                                                                                                                         |
| status                  | completed                                                                                                                               |
| expected_case_count     | 2                                                                                                                                       |
| observed_case_count     | 2                                                                                                                                       |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_c1_v1/report.json |

## Case Summary

|   benchmark_exit_code | case_status   | execution_variant   | label   |   latency_ms_mean |   requests_per_sec |   runtime_sec | skip_reason   | stop_point      |   tpot_ms_mean |   ttft_ms_mean |
|-----------------------|---------------|---------------------|---------|-------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     0 | completed     | runner              | runner  |             65.55 |             15.248 |        16.789 |               | full_completion |              0 |          65.49 |
|                     0 | completed     | myelon              | myelon  |             66.77 |             14.969 |        17.102 |               | full_completion |              0 |          66.71 |
