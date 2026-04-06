# Benchmark Summary

| Key                     | Value                                                                                                                              |
|-------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family        | server_prefill_stress                                                                                                              |
| benchmark_submode       | cache_thrash_round_robin                                                                                                           |
| workload_class          | synthetic_server_prefill_stress                                                                                                    |
| warmup_policy           | measure_first_turn                                                                                                                 |
| first_turn_measured     | True                                                                                                                               |
| arrival_pattern         | saturation_zero_gap                                                                                                                |
| cache_pressure_profile  | hard_thrash                                                                                                                        |
| equivalence_group       |                                                                                                                                    |
| conversation_sampling   | round_robin                                                                                                                        |
| limit_min_tokens        | 8                                                                                                                                  |
| limit_max_tokens        | 8                                                                                                                                  |
| topology_overlay        | tp2                                                                                                                                |
| transport_mode          | socket_vs_myelon_process_runner                                                                                                    |
| build_features          | cuda,myelon,nccl                                                                                                                   |
| effective_device_ids    | [0, 1]                                                                                                                             |
| myelon_rpc_depth        | 8192                                                                                                                               |
| myelon_response_depth   | 8192                                                                                                                               |
| myelon_busy_spin        | True                                                                                                                               |
| prefix_cache_enabled    | True                                                                                                                               |
| prefix_cache_max_tokens | 1024                                                                                                                               |
| kv_fraction             | 0.08                                                                                                                               |
| cpu_mem_fold            | 0.05                                                                                                                               |
| run_class               | fullpass                                                                                                                           |
| result_boundary         | benchmark_failed                                                                                                                   |
| stop_point              | full_completion                                                                                                                    |
| status                  | partial                                                                                                                            |
| expected_case_count     | 2                                                                                                                                  |
| observed_case_count     | 1                                                                                                                                  |
| report_json             | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v6/report.json |

## Case Summary

|   benchmark_exit_code | case_status      |   configured_prefix_cache_blocks |   configured_prefix_cache_tokens | execution_variant   | label   | latency_ms_mean   | observed_cache_pressure_level   | observed_cpu_swap_budget_gb   | observed_cpu_swap_usage_gb_max   | observed_cpu_swap_usage_percent_max   | observed_gpu_kv_budget_gb   | observed_gpu_kv_usage_gb_max   | observed_gpu_kv_usage_percent_max   |   observed_prefix_cache_eviction_count |   observed_prefix_cache_insert_count |   observed_prefix_cache_miss_count |   planned_gpu_blocks |   planned_max_seqs |   planned_tokens_per_seq_limit |   planned_usable_kvcache_tokens | pressure_profile_outcome      | requested_cache_pressure_profile   | requests_per_sec   | result_boundary   | runtime_sec   | skip_reason   | stop_point      | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|------------------|----------------------------------|----------------------------------|---------------------|---------|-------------------|---------------------------------|-------------------------------|----------------------------------|---------------------------------------|-----------------------------|--------------------------------|-------------------------------------|----------------------------------------|--------------------------------------|------------------------------------|----------------------|--------------------|--------------------------------|---------------------------------|-------------------------------|------------------------------------|--------------------|-------------------|---------------|---------------|-----------------|----------------|----------------|
|                     1 | benchmark_failed |                               16 |                             1024 | runner              | runner  |                   |                                 |                               |                                  |                                       |                             |                                |                                     |                                      0 |                                    0 |                                  0 |                 1325 |                  2 |                          40960 |                           84800 | requested_thrash_not_observed | hard_thrash                        |                    | benchmark_failed  |               |               | full_completion |                |                |
