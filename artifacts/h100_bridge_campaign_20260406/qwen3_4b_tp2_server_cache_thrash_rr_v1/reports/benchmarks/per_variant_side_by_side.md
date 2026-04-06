# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            1.03  |          1.069 |          3.7864 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |           33.025 |         30.868 |         -6.5314 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |        16483.3   |      15416.3   |         -6.4732 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |         1618.79  |       1483.8   |         -8.3389 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |        26775.4   |      25802.9   |         -3.632  | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            2     |          2     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |        84544     |      84544     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |           94.4   |         95.2   |          0.8475 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |         84.8   |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |           34     |         33     |         -2.9412 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |           33     |         33     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |           34     |         33     |         -2.9412 | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |          468.41  |        411.47  |        -12.156  | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |          503.909 |        546.013 |          8.3555 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |           33     |         33     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |          463.83  |        411.47  |        -11.2886 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |          485.438 |        545.888 |         12.4527 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |           33     |         33     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |          335.78  |        342.73  |          2.0698 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |            2.503 |          2.451 |         -2.0775 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            1     |          1     |          0      | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            1     |          0     |       -100      | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            6     |          8     |         33.3333 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |           34     |         33     |         -2.9412 | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            3     |          4     |         33.3333 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            3     |          4     |         33.3333 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            6     |          8     |         33.3333 | completed         | completed       |
