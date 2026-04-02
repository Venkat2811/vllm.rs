# B300 Workload

Date: 2026-04-02

## Scope

Track the benchmark workload plan and important findings for `vllm.rs` on the two-GPU B300 host.

## Current Regimes

1. single GPU, default subprocess runner versus Myelon
2. non-disaggregated TP=2 forced runner versus Myelon
3. PD-disagg without TP on two GPUs

## Current Model Ladder

- small: `Qwen/Qwen1.5-0.5B-Chat-GPTQ-Int4`
- medium: `Qwen/Qwen3-4B`
- large: `Qwen/Qwen3.5-27B-FP8`

## Synthetic Harness

First reusable harness:

- script: `scripts/run_myelon_benchmark_matrix.py`
- build profile: `release`
- phases:
  - warmup
  - repeated measured runs
- current modes:
  - `single_gpu`
  - `tp2`
- current workload profiles:
  - `synthetic_short`
  - `synthetic_long_stress`

Important current limitation:

- this binary-path harness captures prompt/decode throughput and elapsed time
- it does not yet expose TTFT or TPOT
- serving-mode benchmarks will be required for those metrics
- the previous long repeated prompt is no longer the default benchmark input; it is now an explicit stress profile

## Dataset Direction

Use two workload classes:

- synthetic control prompt for low-variance comparisons
- ShareGPT-backed serving dataset for mixed prompt lengths and concurrency

Possible future dataset shaping:

- AIBrix-style small / medium / high prompt buckets
- replayable JSONL request stream
- deterministic seed and sampled subset

## Important Findings

### Host bring-up

- B300 host required CUDA `13.0` plus local `cudaforge` `100f` parsing support
- single-GPU CUDA and TP=2 CUDA now work after rebuilding with `CUDA_COMPUTE_CAP=100f`

### Preliminary TP=2 directional results

`Qwen/Qwen3-4B`

- Myelon decode throughput materially improved
- Myelon prompt throughput was slightly worse

`Qwen/Qwen3.5-27B-FP8`

- Myelon prompt throughput improved modestly
- Myelon decode throughput was effectively flat

Interpretation:

- prefill and decode must be reported separately
- smaller models can show IPC sensitivity
- larger models can become compute-bound enough that Myelon no longer changes decode throughput

### TP=2 workload compatibility split

Current evidence is not strong enough to lock the three-model TP=2 ladder yet.

- early one-off short-prompt TP=2 runs succeeded on some cached models
- repeated reruns on the rebased branch have not been stable enough to treat those successes as reproducible
- the old repeated prompt used by the first harness iteration still clearly trips runner-path failures and remains an explicit stress case, not a default benchmark workload
- keep the synthetic short profile as the control workload shape in the harness, but do not mark TP=2 model selection complete until repeatable reruns are archived

### Fresh rerun checkpoint on the rebuilt B300 binary

Current verified TP=2 reruns on the fresh `release` binary:

- `Qwen/Qwen3-4B` passes on forced runner and on `--myelon-ipc`
- `Qwen/Qwen3.5-27B-FP8` passes on forced runner and on `--myelon-ipc`
- both medium and large cached models now show matching local KV-cache geometry per shard during successful runs

Important interpretation:

- the current blocker is no longer "medium and large TP=2 are fundamentally broken on this host"
- the medium and large cached models are usable for the next benchmark-harness iteration
- the small-model slot is still not locked:
  - `Qwen/Qwen3-1.7B` is not fully present in the local cache
  - GPTQ small-model candidates should not be promoted into the benchmark ladder until they pass the same fresh rerun standard
- performance conclusions should still wait for proper warmup plus repeated measured runs; these fresh reruns are functional validation, not the final benchmark artifact

### Single-GPU Myelon server lifecycle fix

Root cause found on the B300 host:

- the first Myelon-backed server request succeeded, but the second request stalled before prefill
- this was not a benchmark-harness bug and not an engine-lock bug
- after Myelon IPC handoff, the runner stops servicing the old local-socket command loop and only consumes the Myelon transport
- `BlockManager::clear_blocks_guard()` still broadcast `MessageType::ClearBlocks` over that abandoned socket path when allocating fresh blocks for the next request
- `ModelRunner::clear_blocks()` is already a no-op, so this was a pure dead-message hang rather than required cleanup

Fix applied in `vllm.rs`:

- `BlockManager` now records whether Myelon IPC is enabled
- `clear_blocks_guard()` skips the socket-side `ClearBlocks` broadcast when Myelon IPC is active

Validation on this host:

- repeated non-streaming Myelon requests now work on one server instance:
  - request 1: `0.769s`
  - request 2: `0.148s`
  - request 3: `0.149s`
- repeated streaming Myelon requests now also work on one server instance
- the upstream multi-turn serving benchmark now completes cleanly against the Myelon server on `Qwen/Qwen3-4B`

Single-GPU upstream serving smoke with Myelon after the fix:

- runtime: `1.830s`
- requests/sec: `3.280`
- warmup runtime: `2.252s`
- TTFT mean: `62.61 ms`
- TPOT mean: `7.29 ms`
- latency mean: `302.76 ms`

Interpretation:

- the previous serving failure was a concrete lifecycle/control-plane bug after Myelon handoff
- the current single-GPU Myelon serving path is now good enough to use for the next benchmark-harness iteration
- remaining benchmark work should move back to methodology and model/regime coverage, not basic repeated-request stability on single GPU

### Single-GPU synthetic serving matrix on B300

Completed with the upstream multi-turn serving benchmark wrapper on one GPU using:

- `synthetic_multi_turn_smoke.json`
- `num_clients=1`
- `max_active_conversations=2`
- `max_num_requests=8`
- `max_turns=2`
- warmup enabled
- measured phase separated from warmup

`Qwen/Qwen1.5-0.5B-Chat-GPTQ-Int4`

- runner: runtime `1.075s`, requests/sec `5.580`, warmup `1.837s`, TTFT `58.51 ms`, TPOT `4.59 ms`, latency `177.22 ms`
- myelon: runtime `1.188s`, requests/sec `5.052`, warmup `1.903s`, TTFT `57.84 ms`, TPOT `4.73 ms`, latency `195.86 ms`

`Qwen/Qwen3-4B`

- runner: runtime `1.816s`, requests/sec `3.305`, warmup `2.787s`, TTFT `63.00 ms`, TPOT `7.23 ms`, latency `300.94 ms`
- myelon: runtime `1.816s`, requests/sec `3.304`, warmup `2.812s`, TTFT `61.10 ms`, TPOT `7.27 ms`, latency `300.46 ms`

`Qwen/Qwen3.5-27B-FP8`

- runner: runtime `39.730s`, requests/sec `0.151`, warmup `50.677s`, TTFT `1420.59 ms`, TPOT `148.23 ms`, latency `6616.56 ms`
- myelon: runtime `39.705s`, requests/sec `0.151`, warmup `50.797s`, TTFT `1417.93 ms`, TPOT `148.19 ms`, latency `6612.31 ms`

Interpretation:

- small model: runner is better on throughput and end-to-end latency; Myelon only edges TTFT slightly
- medium model: runner and Myelon are effectively at parity on this workload
- large model: runner and Myelon are effectively at parity; the workload is compute-bound enough that transport choice does not move the result
- current single-GPU synthetic serving evidence does not support a broad claim that Myelon improves non-TP, non-disaggregated serving throughput on this host
- this slice is still useful because it gives a stable baseline before TP=2, ShareGPT-backed replay, and PD-disagg work

## Next Updates

Add results here when one of these completes:

- first reusable `tp2` benchmark run on all three models
- first ShareGPT-backed serving workload
- first PD-disagg benchmark slice
