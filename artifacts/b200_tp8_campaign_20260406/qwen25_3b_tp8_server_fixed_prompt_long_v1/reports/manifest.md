# Report Manifest

## Identity

| Key                        | Value                                                                                                                            |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | server_prefill_stress                                                                                                            |
| benchmark_submode          | fixed_prompt_burst                                                                                                               |
| model_label                | Qwen/Qwen2.5-3B-Instruct                                                                                                         |
| topology_overlay           | tp8                                                                                                                              |
| tp_scale_overlay           | tp8                                                                                                                              |
| prefill_tp_size            | 8                                                                                                                                |
| decode_tp_size             | 8                                                                                                                                |
| pd_enabled                 | False                                                                                                                            |
| pd_role_layout             |                                                                                                                                  |
| transport_mode             | socket_vs_myelon_process_runner                                                                                                  |
| transport_settings_profile | socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/cpufold0.5                                                 |
| run_class                  | fullpass                                                                                                                         |
| status                     | partial                                                                                                                          |
| result_boundary            | benchmark_failed                                                                                                                 |
| artifact_class             | fullpass/benchmark_failed/full_completion                                                                                        |
| stop_point                 | full_completion                                                                                                                  |
| host                       | weak-time-laughs-fin-03                                                                                                          |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_3b_tp8_server_fixed_prompt_long_v1/report.json |

## Transport Settings

| Key                     | Value                    |
|-------------------------|--------------------------|
| build_features          | cuda,myelon,nccl         |
| effective_device_ids    | [0, 1, 2, 3, 4, 5, 6, 7] |
| myelon_rpc_depth        | 8192                     |
| myelon_response_depth   | 8192                     |
| myelon_busy_spin        | True                     |
| prefix_cache_enabled    | False                    |
| prefix_cache_max_tokens |                          |
| kv_fraction             |                          |
| cpu_mem_fold            | 0.5                      |
| no_stream               | False                    |

## Bundle Paths

| Artifact             | Path                                                                                                                                                                |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| system_snapshot_md   | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_3b_tp8_server_fixed_prompt_long_v1/reports/system_info/system_snapshot.md         |
| benchmark_summary_md | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_3b_tp8_server_fixed_prompt_long_v1/reports/benchmarks/run_summary.md              |
| run_index_md         | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_3b_tp8_server_fixed_prompt_long_v1/reports/benchmarks/run_index.md                |
| side_by_side_md      | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_3b_tp8_server_fixed_prompt_long_v1/reports/benchmarks/per_variant_side_by_side.md |
