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

## Next Updates

Add results here when one of these completes:

- first reusable `single_gpu` benchmark run on all three models
- first reusable `tp2` benchmark run on all three models
- first ShareGPT-backed serving workload
- first PD-disagg benchmark slice
