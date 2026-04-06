# External Python Serving Phase A Results

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Topology: `tp2`
Model: `Qwen/Qwen3-4B`
Server pair:

- baseline: forced runner on `:18080`
- Myelon: `--myelon-ipc` on `:18081`

## Workload

Phase A used a deliberately prompt-heavy serving shape:

- external Python client against the OpenAI-compatible `vllm.rs` server
- fixed prompt, tokenizer-aligned to `1024` tokens
- fixed output cap `16`
- prefix cache disabled on both servers
- non-streaming requests
- `512` total requests per run
- concurrency sweep: `4, 8, 16, 32, 64, 128, 256`

## Client Surface Used

The final retained Phase A runs used [`benchmark_server_fixed_prompt_burst.py`](/root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py), not the upstream multi-turn benchmark and not the SGLang `hicache` client.

Reason:

- the SGLang benchmark pulled in an overly broad Python import surface for this host
- the upstream `vllm` multi-turn benchmark did not provide true in-flight concurrency through `max_active_conversations`; real concurrency was effectively gated by the number of worker processes
- the fixed-prompt burst driver already existed locally and produced real concurrent HTTP bursts against `/v1/chat/completions`

## Result Matrix

| Concurrency | Runner req/s | Myelon req/s | Req/s delta | Runner TTFT ms | Myelon TTFT ms | TTFT delta | Runner latency ms | Myelon latency ms | Latency delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `4` | `8.760` | `9.322` | `+6.42%` | `456.50` | `428.94` | `-6.04%` | `456.50` | `428.95` | `-6.04%` |
| `8` | `11.590` | `12.179` | `+5.08%` | `690.00` | `656.50` | `-4.86%` | `690.00` | `656.51` | `-4.85%` |
| `16` | `14.006` | `14.002` | `-0.03%` | `1141.90` | `1141.89` | `-0.00%` | `1141.91` | `1141.90` | `-0.00%` |
| `32` | `15.244` | `15.537` | `+1.92%` | `2092.75` | `2058.55` | `-1.63%` | `2092.76` | `2058.56` | `-1.63%` |
| `64` | `16.199` | `16.305` | `+0.65%` | `3944.34` | `3922.38` | `-0.56%` | `3944.34` | `3922.38` | `-0.56%` |
| `128` | `16.320` | `16.252` | `-0.42%` | `7445.11` | `7477.78` | `+0.44%` | `7445.11` | `7477.79` | `+0.44%` |
| `256` | `16.395` | `16.417` | `+0.13%` | `12971.81` | `12930.18` | `-0.32%` | `12971.81` | `12930.18` | `-0.32%` |

## Read

- Myelon is visibly positive at low concurrency, but only in the single-digit range.
- The gain collapses quickly as the server approaches saturation.
- Saturation on this host/workload pair is around `16.3 req/s`, reached by roughly `64+` concurrency.
- Once saturated, baseline and Myelon are effectively flat to parity.
- This is a real server-mediated result, not the earlier artifact where the client was only issuing one request at a time.

## Conclusion

Phase A succeeded in answering the narrow question:

- yes, a clean external Python client can show Myelon gains through the HTTP server path
- no, those gains are not remotely close to the old CLI `prefill_stress` multiplier on this `2 x H100` host

Current recommendation:

- stop here and reflect before Phase B
- do not assume a `1024 / 100`, streaming, or ShareGPT realism pass will improve the Myelon story
- if Phase B is run later, it should be framed as a realism check, not as the likely path to a large serving-side win

## Primary Artifacts

- prompt text: [prompt_qwen3_4b_1024tok.txt](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/prompt_qwen3_4b_1024tok.txt)
- runner logs and samples:
  - [runner](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/qwen3_4b_tp2_random_1024_16_nostream/runner)
- Myelon logs and samples:
  - [myelon](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/qwen3_4b_tp2_random_1024_16_nostream/myelon)
