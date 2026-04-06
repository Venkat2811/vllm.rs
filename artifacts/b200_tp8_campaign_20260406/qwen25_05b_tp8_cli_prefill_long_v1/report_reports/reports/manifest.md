# Report Manifest

## Identity

| Key                        | Value                                                                                                                     |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------|
| benchmark_family           | prefill_stress                                                                                                            |
| benchmark_submode          | fixed_prompt_burst                                                                                                        |
| model_label                | Qwen/Qwen2.5-0.5B-Instruct                                                                                                |
| topology_overlay           | tp8                                                                                                                       |
| tp_scale_overlay           | tp8                                                                                                                       |
| prefill_tp_size            | 8                                                                                                                         |
| decode_tp_size             | 8                                                                                                                         |
| pd_enabled                 | False                                                                                                                     |
| pd_role_layout             |                                                                                                                           |
| transport_mode             | socket_vs_myelon_process_runner                                                                                           |
| transport_settings_profile | socket_vs_myelon_process_runner/prefix_off                                                                                |
| run_class                  | quickpass                                                                                                                 |
| status                     | warmup_incomplete_metrics                                                                                                 |
| result_boundary            | benchmark_complete                                                                                                        |
| artifact_class             | quickpass/benchmark_complete/warmup_incomplete_metrics                                                                    |
| stop_point                 | warmup_incomplete_metrics                                                                                                 |
| host                       | weak-time-laughs-fin-03                                                                                                   |
| report_json                | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_05b_tp8_cli_prefill_long_v1/report.json |

## Transport Settings

| Key                     | Value   |
|-------------------------|---------|
| build_features          |         |
| effective_device_ids    |         |
| myelon_rpc_depth        |         |
| myelon_response_depth   |         |
| myelon_busy_spin        |         |
| prefix_cache_enabled    |         |
| prefix_cache_max_tokens |         |
| kv_fraction             |         |
| cpu_mem_fold            |         |
| no_stream               |         |

## Bundle Paths

| Artifact             | Path                                                                                                                                                                        |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| system_snapshot_md   | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_05b_tp8_cli_prefill_long_v1/report_reports/reports/system_info/system_snapshot.md         |
| benchmark_summary_md | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_05b_tp8_cli_prefill_long_v1/report_reports/reports/benchmarks/run_summary.md              |
| run_index_md         | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_05b_tp8_cli_prefill_long_v1/report_reports/reports/benchmarks/run_index.md                |
| side_by_side_md      | /root/Documents/myelon-launch/vllm.rs/artifacts/b200_tp8_campaign_20260406/qwen25_05b_tp8_cli_prefill_long_v1/report_reports/reports/benchmarks/per_variant_side_by_side.md |
