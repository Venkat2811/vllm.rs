# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            2.296 |          2.323 |          1.176  | completed         | completed       |
| runner             | myelon           | runtime_sec                             |           13.935 |         13.774 |         -1.1554 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |          345.442 |        340.742 |         -1.3606 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |           12.365 |         12.217 |         -1.1969 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |          431.997 |        426.262 |         -1.3276 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       583232     |     583232     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |            3     |          3     |          0      | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |            1     |          1     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |           10.64  |         10.67  |          0.282  | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |         4344.36  |       4318.03  |         -0.606  | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |           10.64  |         10.67  |          0.282  | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |         4340.75  |       4314.46  |         -0.6057 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |            2.89  |          2.87  |         -0.692  | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |           92.399 |         93.612 |          1.3128 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |           31     |         31     |          0      | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            0     |          0     |                 | completed         | completed       |
