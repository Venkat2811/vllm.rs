# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            0.535 |          0.523 |         -2.243  | completed         | completed       |
| runner             | myelon           | runtime_sec                             |          299.217 |        306.027 |          2.2759 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |        14817.1   |      14862.3   |          0.3049 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |         6456.74  |       6682.4   |          3.495  | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |        60014.3   |      61639.1   |          2.7074 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       583232     |     583232     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |           38     |         38.7   |          1.8421 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |         2381.97  |       2447.02  |          2.7309 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |          620.64  |        553.778 |        -10.7731 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |         2381.97  |       2447.02  |          2.7309 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |          620.452 |        553.619 |        -10.7717 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |         6889.94  |       7091.12  |          2.9199 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |            0.597 |          0.404 |        -32.3283 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |          128     |        128     |          0      | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            0     |          0     |                 | completed         | completed       |
