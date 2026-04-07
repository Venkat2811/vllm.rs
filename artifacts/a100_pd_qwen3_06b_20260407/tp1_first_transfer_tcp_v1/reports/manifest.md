# Report Manifest

## Identity

| Key                        | Value                                                                                                            |
|----------------------------|------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | pd_qos                                                                                                           |
| benchmark_submode          | first_transfer_control                                                                                           |
| model_label                | Qwen/Qwen3-0.6B                                                                                                  |
| topology_overlay           | pd_tp1                                                                                                           |
| tp_scale_overlay           | pd(tp1/tp1)                                                                                                      |
| prefill_tp_size            | 1                                                                                                                |
| decode_tp_size             | 1                                                                                                                |
| pd_enabled                 | True                                                                                                             |
| pd_role_layout             | same_host_split_roles                                                                                            |
| transport_mode             | pd_tcp                                                                                                           |
| transport_settings_profile | pd_tcp/rpc8192/resp8192/busy_spin/prefix_off                                                                     |
| run_class                  | quickpass                                                                                                        |
| status                     | partial                                                                                                          |
| result_boundary            | benchmark_failed                                                                                                 |
| artifact_class             | quickpass/benchmark_failed/full_completion                                                                       |
| stop_point                 | full_completion                                                                                                  |
| host                       | dark-heart-passes-fin-03                                                                                         |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/a100_pd_qwen3_06b_20260407/tp1_first_transfer_tcp_v1/report.json |

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
| no_stream               | False            |

## Bundle Paths

| Artifact             | Path                                                                                                                                                |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| system_snapshot_md   | /root/Documents/myelon-launch/vllm.rs/artifacts/a100_pd_qwen3_06b_20260407/tp1_first_transfer_tcp_v1/reports/system_info/system_snapshot.md         |
| benchmark_summary_md | /root/Documents/myelon-launch/vllm.rs/artifacts/a100_pd_qwen3_06b_20260407/tp1_first_transfer_tcp_v1/reports/benchmarks/run_summary.md              |
| run_index_md         | /root/Documents/myelon-launch/vllm.rs/artifacts/a100_pd_qwen3_06b_20260407/tp1_first_transfer_tcp_v1/reports/benchmarks/run_index.md                |
| side_by_side_md      | /root/Documents/myelon-launch/vllm.rs/artifacts/a100_pd_qwen3_06b_20260407/tp1_first_transfer_tcp_v1/reports/benchmarks/per_variant_side_by_side.md |
