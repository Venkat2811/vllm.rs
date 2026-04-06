# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |     myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|------------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |      0.536       |      0.516       |         -3.7313 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |    290.888       |    323.572       |         11.2359 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |   7850.27        |   8835.1         |         12.5452 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |   2745.7         |   2716.38        |         -1.0678 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |  27070.2         |  27849.8         |          2.88   | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |      3           |      3           |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           | 126848           | 126848           |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |     75.2         |     93.5         |         24.3351 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |    156           |    167           |          7.0513 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |    156           |    167           |          7.0513 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |    155           |    166           |          7.0968 | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |   1141.07        |   1306.1         |         14.4627 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |   1319.64        |   1327.62        |          0.6048 | completed         | completed       |
| runner             | myelon           | observed_first_token_path_event_count   |    155           |    166           |          7.0968 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_total        | 171380           | 197837           |         15.4376 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |   1105.68        |   1191.79        |          7.7882 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     | 745509           | 823224           |         10.4244 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |   4809.73        |   4959.18        |          3.1072 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_total      | 224166           | 284954           |         27.1174 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_mean       |   1446.23        |   1716.59        |         18.694  | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |      1.14106e+06 |      1.30602e+06 |         14.4568 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |   7361.65        |   7867.56        |          6.8723 | completed         | completed       |
| runner             | myelon           | observed_first_token_flush_count        |    155           |    166           |          7.0968 | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_total         |     11           |      8           |        -27.2727 | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_mean          |      0.071       |      0.048       |        -32.3944 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |    156           |    167           |          7.0513 | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |   1144.79        |   1307.57        |         14.2192 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |   1314.28        |   1329.42        |          1.1527 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |    156           |    167           |          7.0513 | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |   2998.11        |   3243.66        |          8.1902 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |      1.12        |      0.922       |        -17.6786 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |     10           |     19           |         90      | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |    156           |    167           |          7.0513 | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |      3           |      5           |         66.6667 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |      3           |      4           |         33.3333 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |     10           |     19           |         90      | completed         | completed       |
