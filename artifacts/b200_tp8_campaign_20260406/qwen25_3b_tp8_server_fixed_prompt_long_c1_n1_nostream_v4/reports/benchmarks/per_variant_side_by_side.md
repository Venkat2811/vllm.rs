# Per-Variant Side By Side

| baseline_variant   | myelon_variant   | metric                                  |   baseline_value |   myelon_value |   delta_percent | baseline_status   | myelon_status    |
|--------------------|------------------|-----------------------------------------|------------------|----------------|-----------------|-------------------|------------------|
| runner             | myelon           | observed_prefill_event_count            |             1    |           1    |          0      | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_prefill_seconds_total          |             0.8  |           0.85 |          6.25   | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_prefill_tps_mean               |           281.09 |         265.57 |         -5.5214 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_first_token_path_event_count   |             1    |           1    |          0      | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_scheduler_wait_ms_total        |            16    |           9    |        -43.75   | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_scheduler_wait_ms_mean         |            16    |           9    |        -43.75   | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_prefill_roundtrip_ms_total     |           788    |         842    |          6.8528 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_prefill_roundtrip_ms_mean      |           788    |         842    |          6.8528 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_response_to_emit_ms_total      |             0    |           0    |                 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_response_to_emit_ms_mean       |             0    |           0    |                 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_ingress_to_emit_ms_total       |           804    |         851    |          5.8458 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_ingress_to_emit_ms_mean        |           804    |         851    |          5.8458 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_prefix_cache_hit_count         |             0    |           0    |                 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_swap_out_attempt_count         |             0    |           0    |                 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_dropped_request_count          |             0    |           0    |                 | benchmark_failed  | benchmark_failed |
| runner             | myelon           | observed_stream_generation_failed_count |             0    |           0    |                 | benchmark_failed  | benchmark_failed |
