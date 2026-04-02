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

### ShareGPT converter and first realistic serving slice

Important upstream-harness finding:

- the upstream `vllm/benchmarks/multi_turn/convert_sharegpt_to_openai.py` content filter currently accepts non-ASCII messages instead of rejecting them
- `scripts/prepare_myelon_sharegpt_dataset.py` now imports the upstream converter directly and patches that validator to keep ASCII-only content by default, while preserving the rest of the upstream conversion logic

First bounded ShareGPT-derived dataset prepared on this host:

- source: `philschmid/sharegpt-raw` `sharegpt_20230401_clean_lang_split.json`
- output: `artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_128_mt4_8.json`
- seed: `99`
- bounds: `min_turns=4`, `max_turns=8`
- file size: `679 KB`

Token/turn profile of the bounded ShareGPT slice using the local `Qwen/Qwen3-4B` tokenizer:

- turns: min `4`, p50 `7`, p90 `8`, max `8`, mean `6.61`
- total conversation tokens: min `184`, p50 `961`, p90 `1876`, p99 `2797`, max `3530`, mean `1061.34`
- first-user tokens: min `1`, p50 `21`, p90 `99`, p99 `353`, max `399`, mean `43.27`

Interpretation:

- the first bounded ShareGPT slice is realistic enough to create actual context pressure
- `max_model_len=1024` is too tight for this slice; the first real ShareGPT serving run used `max_model_len=4096`

First ShareGPT-backed single-GPU serving A/B on `Qwen/Qwen3-4B`:

- workload: bounded ShareGPT slice, `num_clients=1`, `max_active_conversations=2`, `max_num_requests=16`, `max_turns=4`, `max_model_len=4096`
- runner: runtime `39.188s`, requests/sec `0.383`, warmup `21.742s`, TTFT `70.54 ms`, TPOT `7.10 ms`, latency `2608.66 ms`
- myelon: runtime `39.088s`, requests/sec `0.384`, warmup `21.511s`, TTFT `70.06 ms`, TPOT `7.08 ms`, latency `2602.03 ms`
- both cases used the same measured input/output profile: input tokens mean `303.87`, output tokens mean `368.07`

Additional harness finding:

- the first higher-concurrency attempt on this same ShareGPT slice (`num_clients=2`, `max_active_conversations=4`) stalled after the request-capped runner phase and never advanced cleanly into the rest of the matrix
- the simpler `num_clients=1`, `max_active_conversations=2` configuration completed on both runner and Myelon, so this currently looks like an upstream multi-turn harness/control issue tied to the chosen concurrency shape rather than a basic `vllm.rs` serving correctness failure

### ShareGPT request-cap route-around and higher-concurrency rerun

Follow-up harness finding:

- the earlier higher-concurrency ShareGPT stall was caused by the wrapper always passing `--max-num-requests`
- on upstream multi-turn replay, that hard request cap can stop clients mid-conversation and strand the run
- `scripts/run_myelon_server_benchmark_matrix.py` now omits `--max-num-requests` when the configured value is `0` or lower, so bounded multi-turn replay can run without the bad cap

Smaller higher-concurrency ShareGPT slice used for rerun:

- output: `artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json`
- size: `88 KB`
- workload: `num_clients=2`, `max_active_conversations=4`, `max_turns=4`, `max_model_len=4096`

Single-GPU `Qwen/Qwen3-4B` rerun on that bounded higher-concurrency slice:

- runner: runtime `22.342s`, requests/sec `0.627`, warmup `15.021s`, TTFT `111.84 ms`, TPOT `8.91 ms`, latency `3083.31 ms`
- myelon: runtime `22.699s`, requests/sec `0.617`, warmup `15.236s`, TTFT `85.10 ms`, TPOT `8.90 ms`, latency `3052.62 ms`

Important interpretation:

- the hard stall is gone; the no-cap route-around is the correct fix for this harness shape
- throughput still slightly favors the runner on this slice
- TTFT and end-to-end latency slightly favor Myelon on this slice
- upstream multi-turn replay still terminates a bit awkwardly here: the measured phase ended at `14/16` completed conversations on both runner and Myelon after one client exhausted work and the other received termination, so this is better than the original stall but still not a perfectly clean final serving harness

### First TP=2 serving wrapper runs on the B300 host

TP=2 wrapper bring-up finding:

- the serving wrapper initially launched `num_shards=2` without explicit `--device-ids`, and the server fell back to `[0]`
- `scripts/run_myelon_server_benchmark_matrix.py` now derives `effective_device_ids=[0, 1]` automatically for the 2-shard case when no explicit device list is supplied

First TP=2 synthetic serving run on `Qwen/Qwen3-4B`:

- workload: `synthetic_multi_turn_smoke.json`, `num_clients=1`, `max_active_conversations=2`, `max_num_requests=8`, `max_turns=2`
- runner: runtime `0.315s`, requests/sec `19.031`, TTFT `50.73 ms`, output tokens `0.00`
- myelon: runtime `0.313s`, requests/sec `19.159`, TTFT `50.38 ms`, output tokens `0.00`

First TP=2 ShareGPT-backed serving run on `Qwen/Qwen3-4B`:

- workload: `sharegpt_conv_16_mt4_8.json`, `num_clients=1`, `max_active_conversations=2`, `max_turns=4`, `max_model_len=4096`
- runner: runtime `0.861s`, requests/sec `17.425`, TTFT `55.46 ms`, output tokens `0.00`
- myelon: runtime `0.863s`, requests/sec `17.388`, TTFT `55.59 ms`, output tokens `0.00`

Important interpretation:

- TP=2 serving launch is now functionally green on the wrapper
- but both current TP=2 serving slices are effectively TTFT-only artifacts with no generated output, so they are not yet valid decode or end-to-end serving benchmarks
- the next TP=2 benchmark step should focus on why the current serving path returns `output_num_tokens=0` on these wrapper runs before using this lane for performance conclusions

Direct TP=2 serving probe after the wrapper fix:

- a direct `POST /v1/chat/completions` request against the TP=2 runner server on `Qwen/Qwen3-4B` returned `choices: []` with zero usage counts
- this proves the empty-output issue is not just an upstream benchmark-script artifact
- server-side error during that direct probe:
  - `Runner prefill error: Err(shape mismatch value_cache [512, 4, 128, 64], expected (512, 8, 16, 64, 8))`
  - `Step error: Runner step error, no response!`

Important interpretation:

- the current TP=2 serving blocker is a real multi-shard runtime bug in `vllm.rs`
- this bug affects both the benchmark lane and direct TP=2 serving correctness
- until that prefill/cache-shape mismatch is fixed or a different model/mode avoids it, TP=2 serving latency conclusions on this host are not trustworthy

## Next Updates

Add results here when one of these completes:

- first reusable `tp2` benchmark run on all three models
- first PD-disagg benchmark slice
