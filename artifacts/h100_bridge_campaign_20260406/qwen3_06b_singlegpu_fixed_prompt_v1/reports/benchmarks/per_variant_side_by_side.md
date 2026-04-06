# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |           31.178 |         30.441 |         -2.3638 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |           16.422 |         16.82  |          2.4236 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |         7211.53  |       7369.15  |          2.1857 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |         7246.77  |       7426.57  |          2.4811 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       391552     |     391552     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |          512     |        512     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |         1365.28  |       1382.06  |          1.2291 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |            7.087 |          7.146 |          0.8325 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |          512     |        512     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |         1365.28  |       1382.06  |          1.2291 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |            6.671 |          6.726 |          0.8245 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |          512     |        512     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |           18.05  |         29.59  |         63.9335 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |           67.113 |         55.09  |        -17.9146 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
