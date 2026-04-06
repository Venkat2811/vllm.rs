# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |           30.36  |         30.543 |          0.6028 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |           16.865 |         16.764 |         -0.5989 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            |         7388.17  |       7312.73  |         -1.0211 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         |         7427.24  |       7366.59  |         -0.8166 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |            8     |          8     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           |       391552     |     391552     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |          512     |        512     |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |         1407.04  |       1383     |         -1.7086 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |            6.841 |          6.915 |          1.0817 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |          512     |        512     |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |         1407.04  |       1383     |         -1.7086 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |            6.439 |          6.508 |          1.0716 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |          512     |        512     |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |           19.97  |         27.54  |         37.9069 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |           65.694 |         60.43  |         -8.0129 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |            0     |          0     |                 | completed         | completed       |
