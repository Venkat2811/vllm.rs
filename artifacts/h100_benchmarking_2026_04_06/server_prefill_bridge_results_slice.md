# Server Prefill Bridge Results Slice

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Model: `Qwen/Qwen3-30B-A3B`
Topology: `tp2`
Family: `server_prefill_stress.fixed_prompt_burst`

## What changed

- added a direct HTTP burst driver:
  - `scripts/benchmark_server_fixed_prompt_burst.py`
- split serving and PD warmup semantics explicitly:
  - `serving_qos.cold_turn`
  - `serving_qos.warm_steady_state`
  - `pd_qos.first_transfer_control`
  - `pd_qos.cold_turn`
  - `pd_qos.warm_steady_state`
- retained reports now carry expected case count and treat missing variants as `partial`
- server and PD wrappers now pass the same Myelon transport knobs used by the CLI lane:
  - `--myelon-rpc-depth`
  - `--myelon-response-depth`
  - `--myelon-busy-spin`

## Retained bridge artifacts

- campaign root:
  - `artifacts/h100_bridge_campaign_20260406`
- strongest retained fixed-prompt bridge runs:
  - `qwen30ba3b_tp2_server_fixed_prompt_v4`
  - `qwen30ba3b_tp2_server_fixed_prompt_v256c`
- campaign rollups:
  - `reports/benchmarks/current_findings.md`
  - `reports/benchmarks/per_model_side_by_side.md`
  - `reports/benchmarks/all_run_commands.md`

## Results

### 32-wide burst

- runner:
  - `runtime_sec = 2.913`
  - `requests_per_sec = 10.987`
  - `ttft_ms mean = 2575.74`
  - `latency_ms mean = 2787.55`
- myelon:
  - `runtime_sec = 2.776`
  - `requests_per_sec = 11.529`
  - `ttft_ms mean = 2507.19`
  - `latency_ms mean = 2671.83`
- delta:
  - `+4.93%` requests/sec
  - `-2.66%` TTFT
  - `-4.15%` latency

### 256-wide burst

- runner:
  - `runtime_sec = 14.451`
  - `requests_per_sec = 17.716`
  - `ttft_ms mean = 9671.85`
  - `latency_ms mean = 10390.20`
- myelon:
  - `runtime_sec = 14.201`
  - `requests_per_sec = 18.027`
  - `ttft_ms mean = 9697.25`
  - `latency_ms mean = 10406.74`
- delta:
  - `+1.76%` requests/sec
  - `+0.26%` TTFT
  - `+0.16%` latency

## Interpretation

- the bridge lane is now real and fair:
  - full server path is in the loop
  - first turn is measured
  - same deep-ring and busy-spin Myelon knobs are passed as in the CLI transport-sensitive lane
- even with that fairness fix, the server path still compresses the old prompt win sharply
- the fixed-prompt bridge result is now:
  - clearly positive at `32` burst width
  - nearly flat at `256` burst width
- this means the missing large serving-side gain is not explained by:
  - wrong Myelon depth or wait settings
  - hidden warmup-step skip
  - the old upstream multi-turn `1/32` conversation bug for this submode

## Next

- run the other bridge submodes on H100:
  - `cache_thrash_round_robin`
  - `shared_prefix_round_robin_control`
- if those still stay low-single-digit, move to `VR12` server-path attribution instead of more blind bridge reruns
