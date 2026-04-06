# H100 `serving_qos` Medium-Model TP2 Closure Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`

## Scope

Close the last justified `2 x H100` serving-QoS execution gap on the current host:

- model: `Qwen/Qwen3-4B`
- topology: `tp2`
- family: `serving_qos`
- submodes:
  - `cold_turn_idle_gap`
  - `warm_steady_state`

## New Retained Runs

- `artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_tp2_cold_turn_idle_gap_v1`
- `artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_tp2_warm_steady_state_v1`

## Results

### `cold_turn_idle_gap`

- runner:
  - `1.543 req/s`
  - `137.190 ms` TTFT
  - `331.804 ms` latency
- myelon:
  - `1.531 req/s`
  - `140.265 ms` TTFT
  - `336.905 ms` latency
- read:
  - slight regression under Myelon
  - no evidence of a hidden serving-side gain in this medium-model cold fixed-rate lane

### `warm_steady_state`

- runner:
  - `3.360 req/s`
  - `152.418 ms` TTFT
  - `370.007 ms` latency
- myelon:
  - `3.326 req/s`
  - `157.470 ms` TTFT
  - `369.413 ms` latency
- read:
  - requests/sec is slightly negative under Myelon
  - TTFT is slightly worse under Myelon
  - latency is effectively flat

## Conclusion

This closes the remaining justified `2 x H100` `serving_qos` execution gap.

Current benchmark conclusion on this host is now:

- `prefill_stress`: clearly positive
- `server_prefill_stress`: prompt-path gains survive, but end-to-end serving gains compress materially
- `serving_qos`: medium-model `tp2` closure is flat to slightly negative, not a hidden large-gain lane
- `pd_qos`: benchmarked well enough on supported TCP slices for the current host phase

So the `2 x H100` benchmark phase is now complete enough for current purposes.

Further benchmark expansion should be deferred to:

- `4 x` / `8 x` hosts, or
- post-PR refresh work if upcoming changes materially alter the serving-path story
