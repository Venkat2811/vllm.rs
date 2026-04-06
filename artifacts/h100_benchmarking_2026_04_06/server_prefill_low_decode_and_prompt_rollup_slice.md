# H100 Server-Prefill Low-Decode And Prompt-Rollup Slice

Date: `2026-04-06`

## What Changed

- `scripts/myelon_report_common.py` now promotes server-path prompt metrics into campaign rollups instead of only surfacing CLI-style prompt metrics.
- `high_level_summary.md` now includes:
  - `Strongest Prompt Throughput Gains`
  - `Strongest Prefill-Roundtrip Wins`
- retained H100 bridge campaign rollups were regenerated after landing that reporting slice.

## Validation

- `python3 -m unittest discover -s scripts/tests -v`
- `python3 -m py_compile scripts/myelon_report_common.py scripts/tests/test_benchmark_contract.py`

## New Retained Runs

### `qwen3_4b_tp2_server_low_decode_v1`

- family: `server_prefill_stress.low_decode`
- topology: `tp2`
- model: `Qwen/Qwen3-4B`
- status: `completed`
- pressure outcome:
  - runner: `requested_relaxed_exceeded`
  - Myelon: `requested_relaxed_exceeded`
- observed pressure:
  - runner GPU KV max: `25.5%`
  - Myelon GPU KV max: `16.0%`
  - CPU swap: `0.0%` on both legs
- end-to-end:
  - requests/sec: `0.605 -> 0.609` (`+0.66%`)
  - TTFT: `10515.23 -> 10873.79 ms` (`+3.41%`, worse)
  - latency: `25021.83 -> 25004.65 ms` (`-0.07%`)
- prompt-path attribution:
  - scheduler wait mean: `296.30 -> 261.97 ms` (`-11.58%`)
  - prefill roundtrip mean: `7779.18 -> 7632.83 ms` (`-1.88%`)
  - ingress-to-emit mean: `9499.51 -> 9445.68 ms` (`-0.57%`)
  - prompt t/s mean: `1051.66 -> 1035.02` (`-1.58%`)

Read: this is a clean relaxed bridge baseline, not a strong-gain serving lane.

### `qwen30ba3b_tp2_server_low_decode_v1`

- family: `server_prefill_stress.low_decode`
- topology: `tp2`
- model: `Qwen/Qwen3-30B-A3B`
- status: `completed`
- pressure outcome:
  - runner: `requested_relaxed_exceeded`
  - Myelon: `requested_relaxed_exceeded`
- observed pressure:
  - runner GPU KV max: `29.2%`
  - Myelon GPU KV max: `20.0%`
  - CPU swap: `0.0%` on both legs
- end-to-end:
  - requests/sec: `0.226 -> 0.227` (`+0.44%`)
  - TTFT: `29283.56 -> 28124.97 ms` (`-3.96%`)
  - TPOT: `1241.26 -> 1265.96 ms` (`+1.99%`, worse)
  - latency: `67762.45 -> 67369.73 ms` (`-0.58%`)
- prompt-path attribution:
  - scheduler wait mean: `931.27 -> 331.32 ms` (`-64.42%`)
  - prefill roundtrip mean: `21934.85 -> 19848.18 ms` (`-9.51%`)
  - ingress-to-emit mean: `27030.58 -> 24523.57 ms` (`-9.27%`)
  - prefill t/s mean: `369.13 -> 380.46` (`+3.07%`)
  - prompt t/s mean: `369.07 -> 380.40` (`+3.07%`)

Read: the exact reference-model server bridge still compresses Myelon into a clear prompt-path win with only a tiny end-to-end serving win.

## Current Interpretation

- The new reporting slice fixes a real analysis gap: bridge campaigns no longer look like they lack prompt-path evidence just because they are server-mediated.
- The `low_decode` bridge shape is now clearly established as a relaxed, clean baseline:
  - useful for measuring server-path compression
  - not sufficient by itself to expose a large serving-side Myelon gain
- On the exact reference model, Myelon is still improving the prompt path materially inside the full server flow, but decode and persistent-serving effects compress that into only `+0.44%` end-to-end requests/sec.

## Next Step

- keep the new prompt-path rollups
- use them to evaluate stronger `server_prefill_stress` cache-pressure reruns instead of arguing from end-to-end requests/sec alone
