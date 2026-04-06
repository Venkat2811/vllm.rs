# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            1.444 |          1.412 |         -2.2161 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |          110.791 |        113.307 |          2.2709 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |         5146.7   |       5084.19  |         -1.2146 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |         2363.61  |       2457.88  |          3.9886 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |        21691.9   |      22289.4   |          2.754  | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       581568     |     581568     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |           38.8   |         39.1   |          0.7732 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |          887.19  |        787.89  |        -11.1926 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |         1454.56  |       1752.49  |         20.4824 | completed         | completed       |
| runner             | myelon           | observed_first_token_path_event_count   |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_total        |       148601     |     141943     |         -4.4805 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |          928.756 |        887.144 |         -4.4804 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     |       736516     |     644663     |        -12.4713 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |         4603.23  |       4029.14  |        -12.4713 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_total      |         2049     |       1306     |        -36.2616 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_mean       |           12.806 |          8.162 |        -36.2643 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |       887166     |     787912     |        -11.1878 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |         5544.79  |       4924.45  |        -11.1878 | completed         | completed       |
| runner             | myelon           | observed_first_token_flush_count        |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_total         |           22     |         14     |        -36.3636 | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_mean          |            0.138 |          0.087 |        -36.9565 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |          887.19  |        787.89  |        -11.1926 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |         1454.13  |       1751.98  |         20.4835 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |         2556.28  |       2687.16  |          5.1199 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |            1.405 |          0.887 |        -36.8683 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |          128     |        128     |          0      | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            0     |          0     |                 | completed         | completed       |
