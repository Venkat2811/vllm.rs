# Report Manifest

## Identity

| Key               | Value                                                                                                                           |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family  | server_prefill_stress                                                                                                           |
| benchmark_submode | fixed_prompt_burst                                                                                                              |
| model_label       | Qwen/Qwen3-30B-A3B                                                                                                              |
| topology_overlay  | tp2                                                                                                                             |
| transport_mode    | socket_vs_myelon_process_runner                                                                                                 |
| run_class         | fullpass                                                                                                                        |
| status            | completed                                                                                                                       |
| result_boundary   | benchmark_complete                                                                                                              |
| stop_point        | full_completion                                                                                                                 |
| host              | plain-bear-unfolds-fin-02                                                                                                       |
| report_json       | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/report.json |

## Transport Settings

| Key                     | Value            |
|-------------------------|------------------|
| build_features          | cuda,myelon,nccl |
| effective_device_ids    | [0, 1]           |
| myelon_rpc_depth        | 8192             |
| myelon_response_depth   | 8192             |
| myelon_busy_spin        | True             |
| prefix_cache_enabled    | False            |
| prefix_cache_max_tokens |                  |
| kv_fraction             |                  |
| cpu_mem_fold            | 0.5              |
| no_stream               | False            |

## Bundle Paths

| Artifact             | Path                                                                                                                                                               |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| system_snapshot_md   | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/reports/system_info/system_snapshot.md         |
| benchmark_summary_md | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/reports/benchmarks/run_summary.md              |
| run_index_md         | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/reports/benchmarks/run_index.md                |
| side_by_side_md      | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/reports/benchmarks/per_variant_side_by_side.md |
