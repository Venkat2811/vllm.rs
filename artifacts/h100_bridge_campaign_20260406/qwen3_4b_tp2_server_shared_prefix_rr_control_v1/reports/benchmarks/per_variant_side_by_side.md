# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            1.437 |          1.438 |          0.0696 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |          111.347 |        111.255 |         -0.0826 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |         4842.77  |       4827.47  |         -0.3161 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |         2388.81  |       2401.43  |          0.5283 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |        21564.5   |      21637.5   |          0.3387 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       581568     |     581568     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |           38.6   |         38.6   |          0      | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |          805.17  |        774.38  |         -3.824  | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |         1655.57  |       1791.04  |          8.1824 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |          805.17  |        774.38  |         -3.824  | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |         1655.1   |       1790.54  |          8.1837 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |         2626.1   |       2636.89  |          0.4109 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |            0.914 |          0.89  |         -2.6258 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |          128     |        128     |          0      | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            0     |          0     |                 | completed         | completed       |
