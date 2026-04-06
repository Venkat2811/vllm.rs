# Report Manifest

## Identity

| Key               | Value                                                                                                                                  |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family  | serving_qos                                                                                                                            |
| benchmark_submode | cold_turn_idle_gap                                                                                                                     |
| model_label       | Qwen/Qwen3-0.6B                                                                                                                        |
| topology_overlay  | single_gpu                                                                                                                             |
| transport_mode    | socket_vs_myelon_process_runner                                                                                                        |
| run_class         | fullpass                                                                                                                               |
| status            | completed                                                                                                                              |
| stop_point        | full_completion                                                                                                                        |
| host              | hazy-instance-completes-fin-02                                                                                                         |
| report_json       | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/report.json |

## Transport Settings

| Key                     | Value            |
|-------------------------|------------------|
| build_features          | cuda,myelon,nccl |
| effective_device_ids    |                  |
| myelon_rpc_depth        | 8192             |
| myelon_response_depth   | 8192             |
| myelon_busy_spin        | False            |
| prefix_cache_enabled    | False            |
| prefix_cache_max_tokens |                  |
| kv_fraction             |                  |
| cpu_mem_fold            |                  |
| no_stream               | False            |

## Bundle Paths

| Artifact             | Path                                                                                                                                                                      |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| system_snapshot_md   | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/reports/system_info/system_snapshot.md         |
| benchmark_summary_md | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/reports/benchmarks/run_summary.md              |
| run_index_md         | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/reports/benchmarks/run_index.md                |
| side_by_side_md      | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/reports/benchmarks/per_variant_side_by_side.md |
