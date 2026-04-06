# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                               |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|--------------------------------------|------------------|----------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                     |            2.447 |          2.335 |         -4.577  | completed         | completed       |
| runner             | myelon           | runtime_sec                          |           15.935 |         23.127 |         45.1334 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                         |         7095     |       6413.26  |         -9.6087 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                         |          704.89  |        923.61  |         31.029  | completed         | completed       |
| runner             | myelon           | latency_ms_mean                      |        12029.2   |      12878.5   |          7.0605 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                     |            2     |          2     |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens        |       114816     |     114816     |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max    |           78.2   |         95.8   |         22.5064 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max  |            0     |         89.9   |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count     |           39     |         54     |         38.4615 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count   |           39     |         54     |         38.4615 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count |            0     |          0     |                 | completed         | completed       |
| runner             | myelon           | observed_successful_requests_total   |           39     |         54     |         38.4615 | completed         | completed       |
| runner             | myelon           | observed_failed_requests_total       |            3     |          2     |        -33.3333 | completed         | completed       |
| runner             | myelon           | observed_clients_with_failures       |            3     |          2     |        -33.3333 | completed         | completed       |
| runner             | myelon           | observed_http_422_rejection_count    |            9     |          8     |        -11.1111 | completed         | completed       |
