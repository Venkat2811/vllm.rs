# Benchmark Summary

| Key                    | Value                                                                                                                              |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family       | server_prefill_stress                                                                                                              |
| benchmark_submode      | cache_thrash_round_robin                                                                                                           |
| workload_class         | synthetic_server_prefill_stress                                                                                                    |
| warmup_policy          | measure_first_turn                                                                                                                 |
| first_turn_measured    | True                                                                                                                               |
| arrival_pattern        | saturation_zero_gap                                                                                                                |
| cache_pressure_profile | hard_thrash                                                                                                                        |
| equivalence_group      |                                                                                                                                    |
| conversation_sampling  | round_robin                                                                                                                        |
| limit_min_tokens       | 8                                                                                                                                  |
| limit_max_tokens       | 8                                                                                                                                  |
| topology_overlay       | tp2                                                                                                                                |
| transport_mode         | socket_vs_myelon_process_runner                                                                                                    |
| run_class              | fullpass                                                                                                                           |
| stop_point             | full_completion                                                                                                                    |
| status                 | partial                                                                                                                            |
| expected_case_count    | 2                                                                                                                                  |
| observed_case_count    | 1                                                                                                                                  |
| report_json            | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v6/report.json |

## Case Summary

|   benchmark_exit_code | case_status      | execution_variant   | label   | latency_ms_mean   | requests_per_sec   | runtime_sec   | skip_reason   | stop_point      | tpot_ms_mean   | ttft_ms_mean   |
|-----------------------|------------------|---------------------|---------|-------------------|--------------------|---------------|---------------|-----------------|----------------|----------------|
|                     1 | benchmark_failed | runner              | runner  |                   |                    |               |               | full_completion |                |                |
