# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            1.325 |          1.336 |          0.8302 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |           54.355 |         53.899 |         -0.8389 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |         5048.02  |       4614.25  |         -8.5929 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |           94.156 |        150.585 |         59.9314 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |         5707.11  |       5668.34  |         -0.6793 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       371136     |     371136     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |            3     |          5.3   |         76.6667 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |           72     |         72     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |           72     |         72     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |           72     |         72     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |          346.31  |        295.58  |        -14.6487 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |          496.562 |        590.596 |         18.937  | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |           72     |         72     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |          346.31  |        295.58  |        -14.6487 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |          496.239 |        590.209 |         18.9364 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |           72     |         72     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |           45.44  |         77.85  |         71.3248 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |           21.775 |         16.707 |        -23.2744 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |           72     |         72     |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            0     |          0     |                 | completed         | completed       |
