# H100 Idle-Gap Results Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Campaign root: `artifacts/h100_idle_gap_campaign_20260406`
Model: `Qwen/Qwen3-0.6B`

## Parser fix

The first idle-gap attempt exposed a wrapper bug: `parse_summary()` was not
capturing TTFT and latency averages from the upstream benchmark logs because those
lines are timestamp-prefixed.

That is now fixed, and the retained `v2` reports below carry TTFT and latency means
directly in `report.json`.

## Retained trio

| family | topology | baseline req/s | myelon req/s | delta | baseline TTFT ms | myelon TTFT ms | baseline latency ms | myelon latency ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `serving_qos.cold_turn_idle_gap` | `single_gpu` | 1.881 | 1.880 | -0.05% | 75.543 | 76.525 | 192.051 | 193.289 |
| `serving_qos.cold_turn_idle_gap` | `tp2` | 1.791 | 1.787 | -0.22% | 124.558 | 128.476 | 241.337 | 247.723 |
| `pd_qos.cold_turn_idle_gap` | `pd_tp1` | 1.378 | 1.362 | -1.16% | 291.125 | 291.329 | 396.310 | 395.170 |

## Read

This new non-saturated small-model lane is useful as a semantics and attribution
checkpoint, but it does not currently reveal a stronger Myelon advantage.

Observed pattern:

- `single_gpu`: effectively flat
- `tp2`: slight regression
- `pd_tp1`: slight regression on throughput, near-flat TTFT and latency

## Interpretation

The new idle-gap mode is valid and retained, but on this small model it behaves
more like a realism check than a transport-sensitive win lane.

It does not replace:

- `prefill_stress`
- `server_prefill_stress`

It simply closes the semantics gap for non-saturated arrival.

## Next implication

Do not overinvest in more small-model idle-gap permutations.

If future idle-gap work continues, it should be:

- medium model only if there is a concrete latency question
- otherwise secondary to the main bridge search for a strong serving-side win
