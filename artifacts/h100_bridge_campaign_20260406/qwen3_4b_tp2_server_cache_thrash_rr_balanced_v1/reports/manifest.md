# Report Manifest

## Identity

| Key                        | Value                                                                                                                                     |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | server_prefill_stress                                                                                                                     |
| benchmark_submode          | cache_thrash_round_robin                                                                                                                  |
| model_label                | Qwen/Qwen3-4B                                                                                                                             |
| topology_overlay           | tp2                                                                                                                                       |
| tp_scale_overlay           | tp2                                                                                                                                       |
| prefill_tp_size            | 2                                                                                                                                         |
| decode_tp_size             | 2                                                                                                                                         |
| pd_enabled                 | False                                                                                                                                     |
| pd_role_layout             |                                                                                                                                           |
| transport_mode             | socket_vs_myelon_process_runner                                                                                                           |
| transport_settings_profile | socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix512/kv0.12/cpufold0.2                                                    |
| run_class                  | fullpass                                                                                                                                  |
| status                     | completed                                                                                                                                 |
| result_boundary            | benchmark_complete                                                                                                                        |
| artifact_class             | fullpass/benchmark_complete/full_completion                                                                                               |
| stop_point                 | full_completion                                                                                                                           |
| host                       | hazy-instance-completes-fin-02                                                                                                            |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/report.json |

## Transport Settings

| Key                     | Value            |
|-------------------------|------------------|
| build_features          | cuda,myelon,nccl |
| effective_device_ids    | [0, 1]           |
| myelon_rpc_depth        | 8192             |
| myelon_response_depth   | 8192             |
| myelon_busy_spin        | True             |
| prefix_cache_enabled    | True             |
| prefix_cache_max_tokens | 512              |
| kv_fraction             | 0.12             |
| cpu_mem_fold            | 0.2              |
| no_stream               | False            |

## Bundle Paths

| Artifact             | Path                                                                                                                                                                         |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| system_snapshot_md   | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/reports/system_info/system_snapshot.md         |
| benchmark_summary_md | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/reports/benchmarks/run_summary.md              |
| run_index_md         | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/reports/benchmarks/run_index.md                |
| side_by_side_md      | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/reports/benchmarks/per_variant_side_by_side.md |
