# H100 Small-Model Server-Prefill Attribution Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Campaign root: `artifacts/h100_bridge_campaign_20260406`
Model: `Qwen/Qwen3-0.6B`

## Goal

Use a small stable model to isolate how the full server path responds to:

- topology
- in-flight concurrency
- Myelon wait strategy

under the `server_prefill_stress.fixed_prompt_burst` bridge lane.

## Retained grid

| topology | concurrency | myelon_busy_spin | baseline req/s | myelon req/s | delta |
|---|---:|:---:|---:|---:|---:|
| `single_gpu` | 256 | `true` | 31.178 | 30.441 | -2.36% |
| `single_gpu` | 256 | `false` | 30.360 | 30.543 | +0.60% |
| `single_gpu` | 32 | `true` | 36.517 | 36.873 | +0.97% |
| `single_gpu` | 32 | `false` | 36.192 | 37.638 | +4.00% |
| `single_gpu` | 1 | `false` | 15.248 | 14.969 | -1.83% |
| `tp2` | 256 | `true` | 30.538 | 29.999 | -1.77% |
| `tp2` | 256 | `false` | 30.788 | 30.117 | -2.18% |
| `tp2` | 32 | `true` | 36.786 | 37.011 | +0.61% |
| `tp2` | 32 | `false` | 36.127 | 35.491 | -1.76% |

## Read

The fixed-prompt server bridge is highly shape-sensitive even on a small model.

Observed pattern:

- `single_gpu`
  - `256` concurrent: near-flat to slightly negative unless busy-spin is disabled
  - `32` concurrent: Myelon turns positive, with the best retained result at
    `+4.00%` under `no_spin`
  - `1` concurrent: slightly negative
- `tp2`
  - `256` concurrent: both wait strategies are negative
  - `32` concurrent: only busy-spin stays slightly positive, at `+0.61%`

## Interpretation

This narrows the problem.

- The server path is not simply erasing all Myelon signal.
- The sign and magnitude depend on queueing shape and wait strategy.
- The better Myelon wait strategy is topology-dependent:
  - `single_gpu`: `no_spin` was best in this grid
  - `tp2`: `busy_spin` was best in this grid
- None of these small-model server runs are close to the `>1.5x` bridge target.

## Next implication

The next bridge search should not be another blind fixed-prompt sweep.

Higher-value follow-up is:

- keep the small-model attribution result as a control
- test one medium-model fixed-prompt server control if needed
- focus most new server-side work on stronger cache-pressure and cold-vs-warm
  semantics rather than repeating the same fixed-prompt shape
