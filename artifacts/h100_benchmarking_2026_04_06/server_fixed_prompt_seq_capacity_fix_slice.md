# H100 Server Fixed-Prompt Seq-Capacity Fix Slice

The resumed exact-model fixed-prompt bridge run
`artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v1`
completed successfully, but it exposed a remaining wrapper fairness bug rather than a
new Myelon regression.

## What the completed pre-fix run actually measured

- benchmark family: `server_prefill_stress.fixed_prompt_burst`
- host: `hazy-instance-completes-fin-02`
- model: `Qwen/Qwen3-30B-A3B`
- topology: `tp2`
- requested shape:
  - `256` active conversations
  - `256` max requests
  - repeated long fixed prompt
- actual allocator plan on both runner and Myelon:
  - `planned_max_seqs = 8`
  - `planned_tokens_per_seq_limit = 40960`
  - `planned_usable_kvcache_tokens = 583232`

That happened because the wrapper still left `max_model_len` unset for
`fixed_prompt_burst`, so the server fell back to the full long-context allocator shape
while also keeping the older relaxed `kv_fraction` path. The result is therefore a
queued full-context serving datapoint, not the fair server-side analogue of the CLI
fixed-prompt burst.

## Retained pre-fix result

- runner:
  - `requests_per_sec = 1.268`
  - `observed_prompt_tps_mean = 50.581`
  - `observed_prefill_roundtrip_ms_mean = 5926.969`
  - `observed_scheduler_wait_ms_mean = 56927.062`
- Myelon:
  - `requests_per_sec = 1.273`
  - `observed_prompt_tps_mean = 50.468`
  - `observed_prefill_roundtrip_ms_mean = 5902.609`
  - `observed_scheduler_wait_ms_mean = 57198.664`

This near-parity result is retained as a legitimate "over-queued full-context server"
datapoint, but it should not be used as the bridge comparison against CLI
`prefill_stress.fixed_prompt_burst`.

## Fix now landed

`run_myelon_server_benchmark_matrix.py` now treats `fixed_prompt_burst` as a true
short-context server bridge:

- default `max_model_len = 4096`
- default `kv_fraction` removed from that path
- if `server_prefill_stress` uses either the default or an explicit `max_model_len`,
  the wrapper drops `kv_fraction` before launch
- script tests now assert:
  - retained report `max_model_len == 4096`
  - emitted server command includes `--max-model-len 4096`
  - emitted server command omits `--kv-fraction`

## Next step

Rerun the exact same H100 `Qwen/Qwen3-30B-A3B` `tp2` fixed-prompt bridge with the
corrected `4096`-token server allocator shape, then compare it directly against:

- the retained pre-fix over-queued run above
- the CLI `prefill_stress.fixed_prompt_burst` lane through
  `equivalence_group = fixed_prompt_burst_bridge`
