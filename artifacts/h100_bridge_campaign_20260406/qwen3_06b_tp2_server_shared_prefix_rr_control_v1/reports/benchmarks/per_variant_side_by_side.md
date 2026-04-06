# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |            3.376 |          3.343 |         -0.9775 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |           47.39  |         47.855 |          0.9812 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |         2252.41  |       2236.58  |         -0.7027 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |         1028.17  |       1032.14  |          0.3863 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |         9449.57  |       9461.54  |          0.1267 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       789568     |     789568     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |           28.1   |         28.4   |          1.0676 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |           32     |         32     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |          341.78  |        333.75  |         -2.3495 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |         3634.48  |       3719.83  |          2.3484 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |          341.78  |        333.75  |         -2.3495 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |         3633.49  |       3718.77  |          2.347  | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |         1100.01  |       1114.05  |          1.2764 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |            1.929 |          2.508 |         30.0156 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |          128     |        128     |          0      | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total      |          160     |        160     |          0      | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count       |            0     |          0     |                 | completed         | completed       |
