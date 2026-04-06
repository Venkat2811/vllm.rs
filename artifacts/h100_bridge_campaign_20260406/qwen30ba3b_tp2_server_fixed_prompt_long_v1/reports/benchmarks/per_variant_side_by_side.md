# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |     myelon_value |   delta_percent | baseline_status   | myelon_status   |
|--------------------|------------------|-----------------------------------------|------------------|------------------|-----------------|-------------------|-----------------|
| runner             | myelon           | requests_per_sec                        |      1.268       |      1.273       |          0.3943 | completed         | completed       |
| runner             | myelon           | runtime_sec                             |    201.845       |    201.139       |         -0.3498 | completed         | completed       |
| runner             | myelon           | ttft_ms_mean                            | 106595           | 106358           |         -0.2223 | completed         | completed       |
| runner             | myelon           | tpot_ms_mean                            |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | latency_ms_mean                         | 106683           | 106437           |         -0.2302 | completed         | completed       |
| runner             | myelon           | planned_max_seqs                        |      8           |      8           |          0      | completed         | completed       |
| runner             | myelon           | planned_usable_kvcache_tokens           | 583232           | 583232           |          0      | completed         | completed       |
| runner             | myelon           | observed_gpu_kv_usage_percent_max       |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_cpu_swap_usage_percent_max     |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_miss_count        |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_insert_count      |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_eviction_count    |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_prefill_event_count            |    256           |    256           |          0      | completed         | completed       |
| runner             | myelon           | observed_prefill_seconds_total          |  16090.7         |  16153.9         |          0.3929 | completed         | completed       |
| runner             | myelon           | observed_prefill_tps_mean               |     50.605       |     50.492       |         -0.2233 | completed         | completed       |
| runner             | myelon           | observed_first_token_path_event_count   |    256           |    256           |          0      | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_total        |      1.45733e+07 |      1.46429e+07 |          0.4771 | completed         | completed       |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |  56927.1         |  57198.7         |          0.4771 | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     |      1.5173e+06  |      1.51107e+06 |         -0.411  | completed         | completed       |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |   5926.97        |   5902.61        |         -0.411  | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_total      |     55           |     40           |        -27.2727 | completed         | completed       |
| runner             | myelon           | observed_response_to_emit_ms_mean       |      0.215       |      0.156       |        -27.4419 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |      1.60907e+07 |      1.6154e+07  |          0.3933 | completed         | completed       |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |  62854.2         |  63101.4         |          0.3933 | completed         | completed       |
| runner             | myelon           | observed_first_token_flush_count        |    256           |    256           |          0      | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_total         |     48           |     73           |         52.0833 | completed         | completed       |
| runner             | myelon           | observed_emit_to_flush_ms_mean          |      0.188       |      0.285       |         51.5957 | completed         | completed       |
| runner             | myelon           | observed_prompt_metric_event_count      |    256           |    256           |          0      | completed         | completed       |
| runner             | myelon           | observed_prompt_seconds_total           |  16090.7         |  16153.9         |          0.3929 | completed         | completed       |
| runner             | myelon           | observed_prompt_tps_mean                |     50.581       |     50.468       |         -0.2234 | completed         | completed       |
| runner             | myelon           | observed_decode_metric_event_count      |    256           |    256           |          0      | completed         | completed       |
| runner             | myelon           | observed_decode_seconds_total           |     22.39        |     20.13        |        -10.0938 | completed         | completed       |
| runner             | myelon           | observed_decode_tps_mean                |     20.951       |     22.035       |          5.174  | completed         | completed       |
| runner             | myelon           | observed_prefix_cache_hit_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_swap_out_attempt_count         |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_dropped_request_count          |      0           |      0           |                 | completed         | completed       |
| runner             | myelon           | observed_stream_generation_failed_count |      0           |      0           |                 | completed         | completed       |
