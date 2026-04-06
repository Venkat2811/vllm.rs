# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            1.543 |          1.531 |         -0.7777 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |            4.536 |          4.571 |          0.7716 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |          137.19  |        140.265 |          2.2414 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |            6.419 |          6.486 |          1.0438 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |          331.804 |        336.905 |          1.5374 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |         8192     |       8192     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |            1     |          1     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |            0.31  |          0.32  |          3.2258 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |          653.85  |        631.58  |         -3.406  | completed         | completed       |
| runner             | myelon           | observed_first_token_path_event_count   |            7     |          7     |          0      | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_total        |          165     |        173     |          4.8485 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |           23.571 |         24.714 |          4.8492 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     |          412     |        422     |          2.4272 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |           58.857 |         60.286 |          2.4279 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_total      |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_mean       |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |          577     |        595     |          3.1196 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |           82.429 |         85     |          3.119  | completed         | completed       |
| runner             | myelon           | observed_first_token_flush_count        |            7     |          7     |          0      | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_total         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_mean          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |            7     |          7     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |            0.57  |          0.59  |          3.5088 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |         5422.14  |       5312.42  |         -2.0235 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |            7     |          7     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |            1.51  |          1.52  |          0.6623 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |          158.977 |        157.017 |         -1.2329 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |            7     |          7     |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            0     |          0     |                 | completed         | completed       |
