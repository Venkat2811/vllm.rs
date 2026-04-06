# Server Phase Trace 4B Bridge Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Model: `Qwen/Qwen3-4B`
Topology: `tp2`

## Purpose

Use the new server-path phase tracing on the first clean medium-model bridge/control pair so the retained `server_prefill_stress` results explain where Myelon helps and where end-to-end serving still compresses that gain.

## What Landed

- `vllm.rs` now emits per-sequence first-token path traces from the engine:
  - `scheduler_wait_ms`
  - `prefill_roundtrip_ms`
  - `response_to_emit_ms`
  - `ingress_to_emit_ms`
- the OpenAI server path now emits first-token flush traces:
  - `emit_to_flush_ms`
- retained report parsing now backfills those fields into:
  - raw `report.json`
  - per-run `run_details.csv`
  - per-run `per_variant_side_by_side.{md,csv}`
  - campaign rollups

## Retained Runs

- cache-thrash bridge:
  - `artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v2`
- shared-prefix control:
  - `artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v2`

## Cache-Thrash Result

End-to-end:

- runner: `1.113 req/s`, `16433.34 ms` TTFT, `25191.03 ms` latency
- myelon: `1.053 req/s`, `16109.82 ms` TTFT, `25561.75 ms` latency
- delta:
  - requests/sec: `-5.39%`
  - TTFT: `-1.97%`
  - latency: `+1.47%`

Phase trace:

- scheduler wait mean:
  - runner: `10788.132 ms`
  - myelon: `7867.718 ms`
  - delta: `-27.07%`
- prefill roundtrip mean:
  - runner: `3478.053 ms`
  - myelon: `3577.333 ms`
  - delta: `+2.85%`
- ingress-to-emit mean:
  - runner: `14266.184 ms`
  - myelon: `11445.282 ms`
  - delta: `-19.77%`
- first-token flush mean:
  - runner: `0.0 ms`
  - myelon: `0.051 ms`

Prompt/decode attribution:

- prefill tokens/sec mean:
  - runner: `417.938`
  - myelon: `558.719`
  - delta: `+33.68%`
- prompt tokens/sec mean:
  - runner: `417.843`
  - myelon: `558.591`
  - delta: `+33.68%`
- decode tokens/sec mean:
  - runner: `2.354`
  - myelon: `3.746`
  - delta: `+59.13%`
- failures and rejections:
  - runner: `38` successes, `4` failures, `11` HTTP `422`
  - myelon: `39` successes, `3` failures, `8` HTTP `422`

Read:

- this run is not a “Myelon is slower in the hot path” result
- the hot-path trace says Myelon cut scheduler wait sharply and improved prompt throughput materially
- the end-to-end requests/sec loss comes from the broader serving pipeline and changed runtime mix, not from worse first-token path timing

## Shared-Prefix Control Result

End-to-end:

- runner: `1.444 req/s`, `5146.702 ms` TTFT, `21691.948 ms` latency
- myelon: `1.412 req/s`, `5084.188 ms` TTFT, `22289.355 ms` latency
- delta:
  - requests/sec: `-2.22%`
  - TTFT: `-1.21%`
  - latency: `+2.75%`

Phase trace:

- scheduler wait mean:
  - runner: `928.756 ms`
  - myelon: `887.144 ms`
  - delta: `-4.48%`
- prefill roundtrip mean:
  - runner: `4603.225 ms`
  - myelon: `4029.144 ms`
  - delta: `-12.47%`
- response-to-emit mean:
  - runner: `12.806 ms`
  - myelon: `8.162 ms`
  - delta: `-36.26%`
- ingress-to-emit mean:
  - runner: `5544.79 ms`
  - myelon: `4924.45 ms`
  - delta: `-11.19%`
- first-token flush mean:
  - runner: `0.138 ms`
  - myelon: `0.087 ms`

Prompt/decode attribution:

- prefill tokens/sec mean:
  - runner: `1454.558`
  - myelon: `1752.486`
  - delta: `+20.48%`
- prompt tokens/sec mean:
  - runner: `1454.13`
  - myelon: `1751.98`
  - delta: `+20.48%`
- decode tokens/sec mean:
  - runner: `1.405`
  - myelon: `0.887`
  - delta: `-36.87%`
- both legs are clean:
  - `160` successes
  - `0` failures
  - `0` HTTP `422`

Read:

- even in the bounded shared-prefix control, Myelon still improves prompt-side timings
- the end-to-end requests/sec regression lines up with slower decode throughput on this run, not with worse first-token path timings

## Main Takeaway

The new phase tracing closes a real interpretation gap:

- the server bridge is no longer only “small positive or negative req/s”
- on `Qwen/Qwen3-4B`, Myelon can improve:
  - scheduler wait
  - ingress-to-first-token timing
  - prompt/prefill throughput
  - first-token flush remains negligible on both legs
- so the remaining serving-side compression is not explained by HTTP flush overhead
- it is now more likely a broader decode / scheduler / run-mix issue in the persistent serving path

## Next Step

Use these phase-attributed `4B` runs as the reference control/result pair before any further bridge permutation search:

1. refresh campaign rollups
2. update benchmark/kanban notes with the phase-attribution interpretation
3. only then decide whether the next slice is:
   - deeper decode-path attribution
   - or another cache-pressure shape on the same host
