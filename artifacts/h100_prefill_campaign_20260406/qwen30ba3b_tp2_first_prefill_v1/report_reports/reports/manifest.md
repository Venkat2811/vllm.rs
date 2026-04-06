# Report Manifest

## Identity

| Key               | Value                                                                                                                      |
|-------------------|----------------------------------------------------------------------------------------------------------------------------|
| benchmark_family  | prefill_stress                                                                                                             |
| benchmark_submode | fixed_prompt_burst                                                                                                         |
| model_label       | Qwen/Qwen3-30B-A3B                                                                                                         |
| topology_overlay  | tp2                                                                                                                        |
| transport_mode    | socket_vs_myelon_process_runner                                                                                            |
| run_class         | fullpass                                                                                                                   |
| status            | completed                                                                                                                  |
| result_boundary   | stop_point_limited                                                                                                         |
| stop_point        | first_prefill_completion                                                                                                   |
| host              | hazy-instance-completes-fin-02                                                                                             |
| report_json       | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1/report.json |

## Transport Settings

| Key                     | Value            |
|-------------------------|------------------|
| build_features          | cuda,myelon,nccl |
| effective_device_ids    |                  |
| myelon_rpc_depth        | 8192             |
| myelon_response_depth   | 8192             |
| myelon_busy_spin        | True             |
| prefix_cache_enabled    |                  |
| prefix_cache_max_tokens |                  |
| kv_fraction             |                  |
| cpu_mem_fold            |                  |
| no_stream               |                  |

## Bundle Paths

| Artifact             | Path                                                                                                                                                                         |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| system_snapshot_md   | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1/report_reports/reports/system_info/system_snapshot.md         |
| benchmark_summary_md | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1/report_reports/reports/benchmarks/run_summary.md              |
| run_index_md         | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1/report_reports/reports/benchmarks/run_index.md                |
| side_by_side_md      | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1/report_reports/reports/benchmarks/per_variant_side_by_side.md |
