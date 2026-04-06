# H100 Server Fixed-Prompt OOM Guard Slice

The first rerun after the seq-capacity fix also surfaced a second fairness issue in the
exact-model bridge path.

## Retained runtime-limited artifact

- run directory:
  - `artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v2`
- host:
  - `hazy-instance-completes-fin-02`
- model:
  - `Qwen/Qwen3-30B-A3B`
- topology:
  - `tp2`
- requested bridge shape:
  - `fixed_prompt_burst`
  - `256` active conversations
  - `256` max requests

## What happened

After the earlier seq-capacity fix, `fixed_prompt_burst` was correctly using
`max_model_len = 4096` and no explicit `kv_fraction`. That removed the old
`8 seqs x 40960 tokens` collapse, but it also exposed that exact-model
`4096 x 256` does not fit on the current `2 x H100 80GB` host.

The retained `runner/server.log` shows:

- allocator target:
  - `max_num_seqs = 256`
  - `max_model_len = 4096`
- allocator failure:
  - `KVCache allocation failed: Insufficient GPU memory for KVCache allocation`
  - `Available: 47225.03 MB`
  - `Required: 49152.00 MB`
  - `Reserved: 512.00 MB`

That means this run is a valid runtime-limited bridge datapoint, not a regression result.

## Fix now landed

Two harness corrections are now in code:

1. `fixed_prompt_burst` default `max_model_len` is reduced from `4096` to `2560`
   for the generic bridge lane.
2. `wait_for_server_ready()` now fails fast if the server child exits before
   `/v1/models` becomes ready, instead of waiting for the full readiness timeout.

Script coverage now proves:

- default retained `fixed_prompt_burst` report uses `max_model_len = 2560`
- emitted server command includes `--max-model-len 2560`
- the readiness helper raises immediately when the server exits during startup

## Why `2560`

The fixed prompt itself is the old short repeated burst, not a true long-context serving
case. `2560` is much closer to the historical exact-model TP=2 burst shape and avoids
reintroducing the full long-context allocator distortion.

## Next step

Rerun the exact same `Qwen/Qwen3-30B-A3B` `tp2` fixed-prompt server bridge as:

- `qwen30ba3b_tp2_server_fixed_prompt_long_v3`

with:

- corrected seq-capacity behavior
- `max_model_len = 2560`
- fast-fail startup handling if another allocator issue remains
