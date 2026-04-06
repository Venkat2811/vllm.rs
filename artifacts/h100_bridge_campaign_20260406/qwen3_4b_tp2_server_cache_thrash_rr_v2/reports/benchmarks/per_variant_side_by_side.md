# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            1.113 |          1.053 |         -5.3908 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |           34.154 |         37.024 |          8.4031 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |        16433.3   |      16109.8   |         -1.9687 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |         1251.1   |       1350.28  |          7.9274 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |        25191     |      25561.8   |          1.4716 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            2     |          2     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |        84544     |      84544     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |           89.8   |         76.9   |        -14.3653 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |          542.11  |        446.37  |        -17.6606 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |          417.938 |        558.719 |         33.6847 | completed         | completed       |
| runner             | myelon           | observed_first_token_path_event_count   |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_total        |       409949     |     306841     |        -25.1514 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |        10788.1   |       7867.72  |        -27.0706 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     |       132166     |     139516     |          5.5612 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |         3478.05  |       3577.33  |          2.8545 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_total      |            0     |          9     |                 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_mean       |            0     |          0.231 |                 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |       542115     |     446366     |        -17.6621 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |        14266.2   |      11445.3   |        -19.7733 | completed         | completed       |
| runner             | myelon           | observed_first_token_flush_count        |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_total         |            0     |          2     |                 | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_mean          |            0     |          0.051 |                 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |          542.11  |        446.37  |        -17.6606 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |          417.843 |        558.591 |         33.6844 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |          332.8   |        368.64  |         10.7692 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |            2.354 |          3.746 |         59.1334 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |           11     |          8     |        -27.2727 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |           38     |         39     |          2.6316 | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            4     |          3     |        -25      | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            4     |          3     |        -25      | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |           11     |          8     |        -27.2727 | completed         | completed       |
