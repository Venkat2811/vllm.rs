# B300 Workload

Date: 2026-04-02

## Scope

Track the benchmark workload plan and important findings for `vllm.rs` on the two-GPU B300 host.

## Current Regimes

1. single GPU, default subprocess runner versus Myelon
2. non-disaggregated TP=2 forced runner versus Myelon
3. PD-disagg without TP on two GPUs

## Current Model Ladder

- small: `Qwen/Qwen3-0.6B`
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

### New-host portability checkpoint

Current machine differs materially from the earlier B300 host:

- `2 x NVIDIA RTX PRO 6000 Blackwell Server Edition`
- `~96 GiB` VRAM per GPU
- `60` vCPUs
- `176 GiB` system RAM
- `229 GiB` free on `/` at start of validation

Important build finding:

- the carried-over `release` binaries were invalid on this host and failed immediately with `CUDA_ERROR_INVALID_PTX` while loading `cast_u32_f32`
- a partial rebuild was not enough because `candle-kernels` still reused stale PTX targeting `sm_100f`, and `attention-rs` still reported an old kernel build compute capability of `103`
- a full `cargo clean` plus rebuild with `CUDA_COMPUTE_CAP=120f` was required to regenerate both stacks correctly on this host
- after the full clean rebuild:
  - `attention-rs` kernel build reported compute capability `120`
  - `candle-kernels` PTX regenerated with `.target sm_120f`

Important harness finding:

- `scripts/run_myelon_server_benchmark_matrix.py` no longer hardcodes `CUDA_COMPUTE_CAP=100f`
- the wrapper now only forwards `CUDA_COMPUTE_CAP` when it is explicitly set in the environment, so the benchmark harness does not silently pin the old B300 architecture on newer hosts

Functional validation on the Blackwell server-edition host:

- TP=2 forced-runner CLI generation on `Qwen/Qwen3-4B` is green
- TP=2 Myelon CLI generation on `Qwen/Qwen3-4B` is green
- TP=2 forced-runner server mode on `Qwen/Qwen3-4B` is green:
  - direct `POST /v1/chat/completions` returned a normal completion with nonzero usage counts
- TP=2 Myelon server mode on `Qwen/Qwen3-4B` is green:
  - direct `POST /v1/chat/completions` returned a normal completion with nonzero usage counts
  - repeated requests on one server instance passed `2/2`

Interpretation:

- the earlier TP=2 serving `value_cache` blocker from the B300 notes does not reproduce on this host after a full clean rebuild for `sm_120f`
- on this machine, the next benchmark work should resume from actual warmup-plus-measured A/B runs rather than more TP=2 serving bug hunting

### Blackwell TP=2 root cause correction

The earlier Blackwell TP=2 `value_cache` mismatch was not a new `vllm.rs` model/runtime bug.

- the local Linux helper defaults were still building with `cuda,myelon` instead of `cuda,myelon,nccl`
- without `nccl`, TP greater than 1 launches fell back to the non-NCCL runner path with an effective communicator world size of `1`
- KV cache allocation still used `num_shards=2`, so model attention and cache geometry drifted apart and produced the observed mismatch

Fix applied in the helper layer:

- `scripts/myelon_validation_common.py` now defaults Linux builds to `cuda,myelon,nccl`
- that same helper now fails fast if `num_shards > 1` is requested without `nccl`

Operational requirement on this host:

- multiprocess TP benchmark binaries must be rebuilt with `CUDA_COMPUTE_CAP=120f` and `--features cuda,myelon,nccl`
- after that rebuild, medium-model TP=2 CLI and serving validation are green again for both runner and Myelon

Interpretation:

- the corrected next question is no longer "is medium-model TP=2 broken on Blackwell?"
- the corrected next question is "how do measured TP=2 runner and Myelon compare once the build and topology are valid?"

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

### TP=2 measured serving slices on the Blackwell host

All results below use the corrected Linux build path with `cuda,myelon,nccl`.

Synthetic medium-model TP=2 slice:

- workload: synthetic serving wrapper, warmup separated from measured phase
- model: `Qwen/Qwen3-4B`
- topology: `num_shards=2`
- runner:
  - runtime `2.086s`
  - requests/sec `2.876`
  - warmup runtime `2.700s`
  - TTFT `62.563 ms`
  - TPOT `8.650 ms`
  - latency `346.620 ms`
- myelon:
  - runtime `2.093s`
  - requests/sec `2.866`
  - warmup runtime `2.722s`
  - TTFT `62.911 ms`
  - TPOT `8.671 ms`
  - latency `347.707 ms`

Interpretation:

- medium-model TP=2 synthetic serving is effectively parity between runner and Myelon on this host

ShareGPT-backed medium-model TP=2 slice:

- workload: `sharegpt_conv_16_mt4_8.json`
- topology: `num_shards=2`
- `num_clients=1`
- `max_active_conversations=2`
- `max_num_requests=16`
- `max_turns=2`
- `max_model_len=4096`
- runner:
  - runtime `46.781s`
  - requests/sec `0.321`
  - warmup runtime `26.214s`
  - TTFT `63.418 ms`
  - TPOT `8.531 ms`
  - latency `3116.540 ms`
  - finished `15/16` conversations
- myelon:
  - runtime `46.581s`
  - requests/sec `0.322`
  - warmup runtime `26.244s`
  - TTFT `63.221 ms`
  - TPOT `8.500 ms`
  - latency `3103.271 ms`
  - finished `15/16` conversations

Interpretation:

- medium-model TP=2 ShareGPT-backed serving is also effectively parity, with Myelon only trivially ahead
- the remaining awkwardness in this lane is the upstream multi-turn termination quirk, not a TP=2 cache-shape blocker on the corrected build

### Small-model TP=2 ladder rejection on Blackwell

`Qwen/Qwen1.5-0.5B-Chat-GPTQ-Int4` should not be used as the TP=2 Myelon small-model ladder slot on this host.

- the synthetic TP=2 runner leg completed but did not produce a useful output-token artifact
- the TP=2 Myelon leg crashed with `CUDA_ERROR_ILLEGAL_ADDRESS`

Interpretation:

- this is not a good model candidate for the TP=2 Myelon benchmark ladder on the current host
- do not spend time forcing this GPTQ model into the benchmark matrix just to preserve a nominal small / medium / large label

Replacement chosen on this host:

- `Qwen/Qwen3-0.6B` downloads cleanly (`~1.5G`) and behaves normally on both single-GPU and TP=2 serving slices
- this is the current small-model ladder entry for the Blackwell host benchmark matrix

### Replacement small-model slices on Blackwell: `Qwen/Qwen3-0.6B`

Single-GPU synthetic:

- runner:
  - runtime `1.141s`
  - requests/sec `5.259`
  - warmup runtime `1.512s`
  - TTFT `55.398 ms`
  - TPOT `4.077 ms`
  - latency `182.058 ms`
- myelon:
  - runtime `1.157s`
  - requests/sec `5.184`
  - warmup runtime `1.533s`
  - TTFT `55.909 ms`
  - TPOT `4.146 ms`
  - latency `184.834 ms`

Single-GPU ShareGPT-backed:

- runner:
  - runtime `23.151s`
  - requests/sec `0.648`
  - warmup runtime `13.284s`
  - TTFT `60.531 ms`
  - TPOT `3.928 ms`
  - latency `1568.028 ms`
  - finished `15/16` conversations
- myelon:
  - runtime `23.374s`
  - requests/sec `0.642`
  - warmup runtime `13.384s`
  - TTFT `58.261 ms`
  - TPOT `3.990 ms`
  - latency `1556.395 ms`
  - finished `15/16` conversations

TP=2 synthetic:

- runner:
  - runtime `1.192s`
  - requests/sec `5.032`
  - warmup runtime `1.590s`
  - TTFT `55.482 ms`
  - TPOT `4.318 ms`
  - latency `190.303 ms`
- myelon:
  - runtime `1.190s`
  - requests/sec `5.044`
  - warmup runtime `1.602s`
  - TTFT `54.734 ms`
  - TPOT `4.331 ms`
  - latency `197.113 ms`

TP=2 ShareGPT-backed:

- runner:
  - runtime `23.488s`
  - requests/sec `0.639`
  - warmup runtime `13.906s`
  - TTFT `58.331 ms`
  - TPOT `4.092 ms`
  - latency `1597.240 ms`
  - finished `15/16` conversations
- myelon:
  - runtime `23.545s`
  - requests/sec `0.637`
  - warmup runtime `13.966s`
  - TTFT `58.216 ms`
  - TPOT `4.089 ms`
  - latency `1567.515 ms`
  - finished `15/16` conversations

Interpretation:

- `Qwen/Qwen3-0.6B` is a viable working replacement for the broken GPTQ small-model slot
- single-GPU and TP=2 results are both effectively neutral between runner and Myelon on the current workloads
- the same upstream `15/16` termination quirk remains visible on the bounded ShareGPT replay

### Large-model TP=2 measured slices on Blackwell: `Qwen/Qwen3.5-27B-FP8`

TP=2 synthetic:

- runner:
  - runtime `21.791s`
  - requests/sec `0.275`
  - warmup runtime `28.793s`
  - TTFT `799.696 ms`
  - TPOT `80.767 ms`
  - latency `3501.258 ms`
- myelon:
  - runtime `21.782s`
  - requests/sec `0.275`
  - warmup runtime `28.369s`
  - TTFT `796.963 ms`
  - TPOT `80.769 ms`
  - latency `3498.654 ms`

TP=2 ShareGPT-backed:

- runner:
  - runtime `485.174s`
  - requests/sec `0.031`
  - warmup runtime `280.783s`
  - TTFT `699.655 ms`
  - TPOT `81.663 ms`
  - latency `32341.384 ms`
  - finished `15/16` conversations
- myelon:
  - runtime `485.271s`
  - requests/sec `0.031`
  - warmup runtime `279.978s`
  - TTFT `700.085 ms`
  - TPOT `81.679 ms`
  - latency `32347.693 ms`
  - finished `15/16` conversations

Interpretation:

- the large FP8 TP=2 slices are decisively compute-bound on this host
- runner and Myelon are functionally identical on both synthetic and bounded ShareGPT replay

### Current benchmark-matrix conclusion on the Blackwell host

With the current corrected build, the working non-PD model ladder on this host is:

- small: `Qwen/Qwen3-0.6B`
- medium: `Qwen/Qwen3-4B`
- large: `Qwen/Qwen3.5-27B-FP8`

Across that ladder:

- single-GPU non-disaggregated serving is effectively parity between runner and Myelon
- TP=2 non-disaggregated serving is also effectively parity between runner and Myelon
- the current repeated artifact is not "Myelon wins throughput" but rather "Myelon does not materially change end-to-end serving on these controlled Blackwell workloads"
- the remaining benchmark gap is PD-disaggregation, not basic non-PD process A/B coverage

### PD-disagg bring-up checkpoint on Blackwell

The first same-node PD-disagg LocalIPC smoke is green with the replacement small model.

- PD server: GPU `0`, `Qwen/Qwen3-0.6B`, `--pd-server --prefix-cache --force-runner`
- PD client: GPU `1`, `Qwen/Qwen3-0.6B`, `--server --port 18080 --pd-client --prefix-cache --force-runner`
- transport: implicit CUDA LocalIPC (`pd_url` omitted)
- result: `GET /v1/models` on the PD client returned normally, the PD server accepted the LocalIPC connection, and a real `POST /v1/chat/completions` request returned a completion with nonzero usage counts

Observed smoke response:

- prompt tokens `15`
- completion tokens `12`
- prefill `0.12s`
- decode `0.04s`

Interpretation:

- the current host and model ladder are good enough to start a real PD baseline harness next
- the next work is methodology, not basic PD wiring

### PD-disagg benchmark results on the Blackwell VM

The first real PD benchmark pass is now split into three distinct outcomes on `Qwen/Qwen3-0.6B`.

1. LocalIPC same-node PD benchmark is not usable on this VM for real KV transfer.

- workload: `synthetic_multi_turn_smoke.json`, `num_clients=1`, `max_active_conversations=2`, `max_num_requests=8`, `max_turns=2`, warmup enabled
- runner PD setup launched and the benchmark process itself exited `0`, but the real PD path failed during KV receive
- failing client-side error:
  - `KvCacheReceive failed: Err(cuIpcOpenMemHandle_v2 failed: DriverError(CUDA_ERROR_PEER_ACCESS_UNSUPPORTED, "peer access is not supported between these two devices"))`
- downstream symptom:
  - sequences aborted after prefill transfer failure
  - measured outputs degraded to `output_num_tokens avg: 0.000`

Interpretation:

- the earlier LocalIPC smoke only proved control-plane bring-up and a light request path
- this KVM Blackwell VM does not expose the GPU peer-access path needed for real LocalIPC PD KV transfer between GPU `0` and GPU `1`
- LocalIPC PD A/B numbers on this host are therefore not meaningful for performance conclusions

2. TCP PD baseline on the same host is valid for the current runner path.

- transport: `tcp://127.0.0.1:18100`
- workload: `synthetic_multi_turn_smoke.json`, `num_clients=1`, `max_active_conversations=2`, `max_num_requests=8`, `max_turns=2`, warmup enabled
- result: runner PD completed cleanly
- measured runner PD synthetic result:
  - runtime `1.218s`
  - requests/sec `4.926`
  - warmup `2.396s`
  - total runtime incl warmup `3.614s`
  - TTFT `56.027 ms`
  - TPOT `4.388 ms`
  - latency `192.912 ms`
  - input tokens mean `431.6`
  - output tokens mean `32.4`

3. Current Myelon PD path is still hanging on real transferred prefill, even after routing PD over TCP.

- synthetic TCP run with warmup and `max_active_conversations=2` stalled after the client accepted the next request
- narrower fallback run was used to remove concurrency and warmup from the equation:
  - workload: `pd_inputs/pd_transfer_first_request.json`
  - one conversation
  - one measured request
  - no warmup
  - first request forced to `578` input tokens / `32` output tokens target
- runner PD fallback completed cleanly:
  - runtime `0.567s`
  - requests/sec `1.764`
  - TTFT `429.73 ms`
  - TPOT `4.43 ms`
  - latency `566.95 ms`
- Myelon PD fallback still hung

Exact observed stop point on the failing Myelon PD fallback:

- client log:
  - `Prefill request (Seq 0, 586 tokens) transfered to PD server.`
- PD server log:
  - `PD Server: received TransferPrefill for Seq 0 (586 tokens)`
  - `Runner configuring Myelon transport ...`
  - `Enabled Myelon IPC hot path across 1 runner(s).`
  - `Dispatching first Myelon request kind=1 bytes=2502.`
  - `Runner entered Myelon hot path with first kind=1 bytes=2502.`
  - `Runner sent first Myelon response bytes=12.`
  - `Received first Myelon response kind=100 bytes=12.`
- and then no further progress

Interpretation:

- current PD-disagg status on this VM is not "Myelon slower" or "Myelon faster"
- the current status is:
  - runner PD over TCP is benchmarkable and green
  - LocalIPC PD is blocked by VM peer-access limits
  - Myelon PD hangs as soon as a real transferred prefill enters the Myelon hot path
- the next PD step is debugging the Myelon-plus-PD interaction after first transferred prefill, not collecting more broad PD performance data

### PD/Myelon codepath finding

The current TCP Myelon PD hang is now explained by the implementation, not just by runtime symptoms.

Current PD server flow in process-runner mode:

- scheduler receives `TransferPrefill`
- prefill runs
- PD server `postprocess()` calls `BlockManager::try_send_kvcache()`
- that sends `MessageType::KvCacheSend` over the legacy local socket control path
- the subprocess runner is expected to handle that by calling `ModelRunner::send_kvcache()`

But once Myelon is enabled:

- engine sends `InitMyelonTransport`
- the subprocess runner attaches to Myelon
- the runner then breaks out of the legacy socket command loop and enters the Myelon loop
- the Myelon loop currently only handles:
  - `RunPrefill`
  - `RunDecode`
  - `FinishDecode`
  - `Cancel`
  - `Shutdown`

It does not handle the PD helper verbs such as:

- `KvCacheSend`
- `KvCacheReceive`
- `TransferPrefill`
- `ReceivePrefill`
- release / status checks

The regenerated TCP Myelon artifact now shows the exact stall point with the new debug logs:

- PD server:
  - `Runner switching execution to Myelon hot path; legacy local-socket control handling will stop after this handshake.`
  - `PD Server: seq 0 reached postprocess under Myelon IPC; requesting KvCacheSend over the runner control path.`
- and after that there is no `Runner received KvCacheSend ...`

Interpretation:

- current Myelon PD on process runners is structurally incomplete for the existing PD KV-export model
- before PD + Myelon can work, one of these has to change:
  - add PD helper verbs to the Myelon protocol
  - keep the legacy control loop alive alongside Myelon
  - avoid enabling Myelon on PD server runners
- this is separate from TP inside prefill/decode nodes; TP-within-node can still be pursued even if current PD server KV export is not Myelon-compatible yet

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

- first Myelon PD fix and successful TCP PD A/B rerun
