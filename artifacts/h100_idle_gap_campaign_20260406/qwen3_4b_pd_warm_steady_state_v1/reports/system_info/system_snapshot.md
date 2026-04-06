# System Snapshot

## Key Facts

| Key                        | Value                                         |
|----------------------------|-----------------------------------------------|
| hostname                   | hazy-instance-completes-fin-02                |
| system                     | Linux                                         |
| release                    | 6.8.0-100-generic                             |
| platform                   | Linux-6.8.0-100-generic-x86_64-with-glibc2.39 |
| machine                    | x86_64                                        |
| python_version             | 3.12.3                                        |
| cpu_count                  | 80                                            |
| cuda_visible_devices       |                                               |
| cuda_compute_cap_override  | 90                                            |
| detected_cuda_device_count | 2                                             |
| effective_device_ids       | [0, 1]                                        |

## Repo State

| Key       | Value                                                                                          |
|-----------|------------------------------------------------------------------------------------------------|
| repo_path | /root/Documents/myelon-launch/vllm.rs                                                          |
| branch    | myelon-integration-1                                                                           |
| commit    | f6e88c7336ef5973bbd515472f94a03dc0b2f6a1                                                       |
| status    | M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/all_run_commands.md             |
|           |  M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/current_findings.csv           |
|           |  M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/current_findings.md            |
|           |  M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/high_level_summary.md          |
|           |  M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/per_model_side_by_side.csv     |
|           |  M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/per_model_side_by_side.md      |
|           |  M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/rollup_run_index.csv           |
|           |  M artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/rollup_run_index.md            |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_cold_turn_idle_gap_v1/                |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/                 |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/bridge_attribution_summary.csv |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/bridge_attribution_summary.md  |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/by_artifact_class/             |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/by_family/                     |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/by_pressure_outcome_pair/      |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/by_result_boundary/            |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/by_run_class/                  |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/by_topology/                   |
|           | ?? artifacts/h100_idle_gap_campaign_20260406/reports/benchmarks/by_workload/                   |

## Raw Command Captures

| Capture                 | Path                                                                                                                                                     |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| df_h.txt                | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/raw/system_info/df_h.txt                |
| free_h.txt              | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/raw/system_info/free_h.txt              |
| hostnamectl.txt         | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/raw/system_info/hostnamectl.txt         |
| lscpu.txt               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/raw/system_info/lscpu.txt               |
| nvidia_smi.txt          | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/raw/system_info/nvidia_smi.txt          |
| nvidia_smi_topology.txt | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/raw/system_info/nvidia_smi_topology.txt |
| uname.txt               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/raw/system_info/uname.txt               |
