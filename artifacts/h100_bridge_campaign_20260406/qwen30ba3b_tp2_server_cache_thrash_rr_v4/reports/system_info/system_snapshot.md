# System Snapshot

## Key Facts

| Key                        | Value                                         |
|----------------------------|-----------------------------------------------|
| hostname                   | plain-bear-unfolds-fin-02                     |
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

| Key       | Value                                                                                                   |
|-----------|---------------------------------------------------------------------------------------------------------|
| repo_path | /root/Documents/myelon-launch/vllm.rs                                                                   |
| branch    | myelon-integration-1                                                                                    |
| commit    | 602c1c1e73633f989d6e22fb36c7e8e713263853                                                                |
| status    | M artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json |
|           |  M artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json       |
|           |  M artifacts/h100_bridge_campaign_20260406/reports/benchmarks/all_run_commands.md                       |
|           |  M artifacts/h100_bridge_campaign_20260406/reports/benchmarks/current_findings.csv                      |
|           |  M artifacts/h100_bridge_campaign_20260406/reports/benchmarks/current_findings.md                       |
|           |  M artifacts/h100_bridge_campaign_20260406/reports/benchmarks/per_model_side_by_side.csv                |
|           |  M artifacts/h100_bridge_campaign_20260406/reports/benchmarks/per_model_side_by_side.md                 |
|           |  M artifacts/h100_bridge_campaign_20260406/reports/benchmarks/rollup_run_index.csv                      |
|           |  M artifacts/h100_bridge_campaign_20260406/reports/benchmarks/rollup_run_index.md                       |
|           |  M scripts/myelon_report_common.py                                                                      |
|           |  M scripts/run_myelon_server_benchmark_matrix.py                                                        |
|           |  M scripts/tests/test_benchmark_contract.py                                                             |
|           | ?? artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v1/                    |
|           | ?? artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v2/                    |
|           | ?? artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v3/                    |
|           | ?? artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/                    |
|           | ?? artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256d/                    |
|           | ?? artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v1/           |

## Raw Command Captures

| Capture                 | Path                                                                                                                                                           |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| df_h.txt                | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/raw/system_info/df_h.txt                |
| free_h.txt              | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/raw/system_info/free_h.txt              |
| hostnamectl.txt         | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/raw/system_info/hostnamectl.txt         |
| lscpu.txt               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/raw/system_info/lscpu.txt               |
| nvidia_smi.txt          | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/raw/system_info/nvidia_smi.txt          |
| nvidia_smi_topology.txt | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/raw/system_info/nvidia_smi_topology.txt |
| uname.txt               | /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/raw/system_info/uname.txt               |
