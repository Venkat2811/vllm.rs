# Rollup Identity And Fixed-Prompt V3 Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`

## What Landed

- retained rollups now carry at-a-glance artifact identity:
  - `artifact_class`
  - `transport_settings_profile`
- grouped rollups now also emit:
  - `by_result_boundary/...`
  - `by_artifact_class/...`
  - `by_pressure_outcome_pair/...`
- campaign summaries now include `Pressure Outcome Pair Counts`
- command catalogs now print `artifact_class` and `transport_settings_profile` per retained run

## Validation

- `python3 -m unittest discover -s scripts/tests -v`
- `python3 -m py_compile scripts/myelon_report_common.py scripts/myelon_validation_common.py scripts/run_myelon_benchmark_matrix.py scripts/run_myelon_server_benchmark_matrix.py scripts/run_myelon_pd_benchmark_matrix.py scripts/tests/test_benchmark_contract.py`

## Exact-Model Bridge Result

Fair retained run:

- artifact: `artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v3`
- model: `Qwen/Qwen3-30B-A3B`
- topology: `tp2`
- family: `server_prefill_stress.fixed_prompt_burst`
- host: `2 x H100 80GB`
- key fairness settings:
  - `max_model_len = 2560`
  - `max_num_seqs = 256`
  - `max_active_conversations = 256`
  - direct HTTP fixed-prompt burst client
  - Myelon `8192 / 8192` plus busy-spin

Observed outcome:

- runner `requests_per_sec = 1.233`
- myelon `requests_per_sec = 1.237`
- delta `+0.32%`
- runner `ttft_ms_mean = 138786.76`
- myelon `ttft_ms_mean = 138348.90`
- delta `-0.32%`
- runner `latency_ms_mean = 139241.82`
- myelon `latency_ms_mean = 138814.13`
- delta `-0.31%`
- observed GPU KV max:
  - runner `25.8%`
  - myelon `31.9%`
- observed CPU swap max:
  - runner `0.0%`
  - myelon `0.0%`
- retained pressure outcome:
  - runner `requested_relaxed_exceeded`
  - myelon `requested_relaxed_exceeded`

## Interpretation

- this closes the remaining fairness gap for the exact-model fixed-prompt server bridge on the current H100 host
- once allocator collapse and startup-OOM distortions are removed, the full persistent-server path is effectively near-flat on this exact-model fixed-prompt burst
- that means the next serving-side gain hunt should not repeat fixed-prompt fairness work
- the next useful 2-GPU work is:
  - stronger cache-pressure server shapes
  - or deeper attribution explaining why prompt-path wins are still being compressed in persistent serving
