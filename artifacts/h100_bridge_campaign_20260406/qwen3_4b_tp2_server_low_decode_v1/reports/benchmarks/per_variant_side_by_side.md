# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |     myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|------------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |      0.605       |      0.609       |          0.6612 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |    290.871       |    289.16        |         -0.5882 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |  10515.2         |  10873.8         |          3.4099 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |    467.955       |    455.834       |         -2.5902 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |  25021.8         |  25004.7         |         -0.0686 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |      8           |      8           |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           | 581568           | 581568           |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |     25.5         |     16           |        -37.2549 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |   1671.82        |   1662.42        |         -0.5623 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |   1051.83        |   1035.19        |         -1.5818 | completed         | completed       |
| runner             | myelon           | observed_first_token_path_event_count   |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_total        |  52148           |  46107           |        -11.5843 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |    296.295       |    261.972       |        -11.5841 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     |      1.36914e+06 |      1.34338e+06 |         -1.8813 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |   7779.18        |   7632.83        |         -1.8813 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_total      | 250631           | 272954           |          8.9067 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_mean       |   1424.04        |   1550.88        |          8.9067 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |      1.67191e+06 |      1.66244e+06 |         -0.5667 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |   9499.51        |   9445.68        |         -0.5667 | completed         | completed       |
| runner             | myelon           | observed_first_token_flush_count        |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_total         |     15           |     24           |         60      | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_mean          |      0.085       |      0.136       |         60      | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |   1671.82        |   1662.42        |         -0.5623 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |   1051.66        |   1035.02        |         -1.5822 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |   2576.81        |   2563.04        |         -0.5344 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |      3.814       |      3.19        |        -16.3608 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |      0           |      0           |                 | completed         | completed       |
