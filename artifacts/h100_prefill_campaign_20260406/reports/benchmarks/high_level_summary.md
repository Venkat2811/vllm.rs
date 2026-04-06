# High-Level Summary

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406`
- reports_found: `4`
- completed_runs: `2`
- incomplete_or_skipped_runs: `2`

## Strongest Requests/sec Gains

No completed baseline/Myelon comparisons were available.

## Strongest TTFT Wins

No TTFT deltas were available.

## Strongest Prompt Throughput Gains

| model_label        | benchmark_family   | benchmark_submode   | topology_overlay   |   prompt_tps_delta_percent |   baseline_prompt_tps_mean |   myelon_prompt_tps_mean |   baseline_first_prefill_seconds_mean |   myelon_first_prefill_seconds_mean |
|--------------------|--------------------|---------------------|--------------------|----------------------------|----------------------------|--------------------------|---------------------------------------|-------------------------------------|
| Qwen/Qwen3-30B-A3B | prefill_stress     | fixed_prompt_burst  | tp2                |                     7.3895 |                   1401.14  |                  1504.67 |                                  1.48 |                                1.36 |
| Qwen/Qwen3-30B-A3B | prefill_stress     | fixed_prompt_burst  | tp2                |                     0.1139 |                      7.022 |                     7.03 |                                  2.42 |                                2.42 |

## Strongest First-Prefill Wins

| model_label        | benchmark_family   | benchmark_submode   | topology_overlay   |   first_prefill_seconds_delta_percent |   baseline_first_prefill_seconds_mean |   myelon_first_prefill_seconds_mean |   baseline_first_prefill_tps_mean |   myelon_first_prefill_tps_mean |
|--------------------|--------------------|---------------------|--------------------|---------------------------------------|---------------------------------------|-------------------------------------|-----------------------------------|---------------------------------|
| Qwen/Qwen3-30B-A3B | prefill_stress     | fixed_prompt_burst  | tp2                |                               -8.1081 |                                  1.48 |                                1.36 |                            11.63  |                           12.49 |
| Qwen/Qwen3-30B-A3B | prefill_stress     | fixed_prompt_burst  | tp2                |                                0      |                                  2.42 |                                2.42 |                             7.022 |                            7.03 |

## Notable Regressions

No completed baseline/Myelon comparisons were available.

## Incomplete / Unsupported

| model_label        | benchmark_family   | benchmark_submode   | topology_overlay   | status                    | skip_reason   | report_json                                                                                                                      |
|--------------------|--------------------|---------------------|--------------------|---------------------------|---------------|----------------------------------------------------------------------------------------------------------------------------------|
| Qwen/Qwen3-30B-A3B | prefill_stress     | fixed_prompt_burst  | tp2                | warmup_incomplete_metrics |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch256_v2/report.json |
| Qwen/Qwen3-30B-A3B | prefill_stress     | fixed_prompt_burst  | tp2                | warmup_incomplete_metrics |               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_v1/report.json          |
