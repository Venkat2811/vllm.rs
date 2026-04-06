# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |     myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|------------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |      0.226       |      0.227       |          0.4425 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |    779.876       |    775.117       |         -0.6102 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |  29283.6         |  28125           |         -3.9565 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |   1241.26        |   1265.96        |          1.9903 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |  67762.5         |  67369.7         |         -0.5796 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |      8           |      8           |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           | 583232           | 583232           |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |     29.2         |     20           |        -31.5068 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |   4757.38        |   4316.1         |         -9.2757 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |    369.129       |    380.456       |          3.0686 | completed         | completed       |
| runner             | myelon           | observed_first_token_path_event_count   |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_total        | 163904           |  58313           |        -64.4225 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |    931.273       |    331.324       |        -64.4225 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     |      3.86053e+06 |      3.49328e+06 |         -9.513  | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |  21934.8         |  19848.2         |         -9.513  | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_total      | 732946           | 764557           |          4.3129 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_mean       |   4164.47        |   4344.07        |          4.3129 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |      4.75738e+06 |      4.31615e+06 |         -9.2747 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |  27030.6         |  24523.6         |         -9.2747 | completed         | completed       |
| runner             | myelon           | observed_first_token_flush_count        |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_total         |      9           |     36           |        300      | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_mean          |      0.051       |      0.205       |        301.961  | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |   4757.38        |   4316.1         |         -9.2757 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |    369.07        |    380.397       |          3.0691 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |   6872.77        |   6979.68        |          1.5556 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |      1.393       |      1.236       |        -11.2706 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |    176           |    176           |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |      0           |      0           |                 | completed         | completed       |
