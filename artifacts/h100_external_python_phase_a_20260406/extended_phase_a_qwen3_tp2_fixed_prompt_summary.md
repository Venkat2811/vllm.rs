# External Python Serving Extended Phase A Results

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Topology: `tp2`
Server pair:

- baseline: forced runner on `:18080`
- Myelon: `--myelon-ipc` on `:18081`

## Scope

Extended Phase A stayed inside the same no-code external-client lane:

- external Python burst client against the `vllm.rs` OpenAI-compatible server
- fixed prompt, `1024` plain tokens on both `Qwen3-4B` and `Qwen3-0.6B`
- non-streaming requests
- prefix cache disabled
- `256` total requests per run
- concurrency sweep: `1, 2, 4, 8, 16, 32, 64`

Shapes executed:

- `Qwen/Qwen3-4B`, `max_tokens=1`
- `Qwen/Qwen3-4B`, `max_tokens=4`
- `Qwen/Qwen3-0.6B`, `max_tokens=1`
- `Qwen/Qwen3-0.6B`, `max_tokens=4`

## Result Matrix

### `Qwen/Qwen3-4B`, `1024 / 1`, non-stream

| Concurrency | Runner req/s | Myelon req/s | Req/s delta | Runner TTFT ms | Myelon TTFT ms | TTFT delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1` | `7.380` | `7.406` | `+0.35%` | `135.46` | `134.99` | `-0.35%` |
| `2` | `9.400` | `9.138` | `-2.79%` | `212.69` | `218.32` | `+2.65%` |
| `4` | `11.799` | `10.928` | `-7.38%` | `337.06` | `364.85` | `+8.24%` |
| `8` | `13.723` | `13.868` | `+1.06%` | `576.72` | `570.78` | `-1.03%` |
| `16` | `15.507` | `15.481` | `-0.17%` | `1019.86` | `1021.74` | `+0.18%` |
| `32` | `17.106` | `16.495` | `-3.57%` | `1789.22` | `1883.39` | `+5.26%` |
| `64` | `17.314` | `16.957` | `-2.06%` | `3540.13` | `3593.18` | `+1.50%` |

### `Qwen/Qwen3-4B`, `1024 / 4`, non-stream

| Concurrency | Runner req/s | Myelon req/s | Req/s delta | Runner TTFT ms | Myelon TTFT ms | TTFT delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1` | `6.222` | `6.236` | `+0.23%` | `160.67` | `160.32` | `-0.22%` |
| `2` | `7.808` | `8.178` | `+4.74%` | `256.04` | `244.45` | `-4.53%` |
| `4` | `10.431` | `11.033` | `+5.77%` | `383.22` | `362.43` | `-5.43%` |
| `8` | `13.273` | `13.843` | `+4.29%` | `602.55` | `577.58` | `-4.14%` |
| `16` | `15.194` | `15.360` | `+1.09%` | `1052.36` | `1040.85` | `-1.09%` |
| `32` | `16.615` | `16.226` | `-2.34%` | `1924.78` | `1968.29` | `+2.26%` |
| `64` | `17.085` | `16.882` | `-1.19%` | `3738.97` | `3786.68` | `+1.28%` |

### `Qwen/Qwen3-0.6B`, `1024 / 1`, non-stream

| Concurrency | Runner req/s | Myelon req/s | Req/s delta | Runner TTFT ms | Myelon TTFT ms | TTFT delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1` | `11.602` | `11.822` | `+1.90%` | `86.15` | `84.54` | `-1.87%` |
| `2` | `15.054` | `14.983` | `-0.47%` | `132.79` | `133.26` | `+0.35%` |
| `4` | `20.914` | `19.787` | `-5.39%` | `189.62` | `201.58` | `+6.31%` |
| `8` | `29.218` | `29.938` | `+2.46%` | `271.00` | `267.08` | `-1.45%` |
| `16` | `35.184` | `39.402` | `+11.99%` | `442.08` | `395.85` | `-10.46%` |
| `32` | `41.210` | `39.905` | `-3.17%` | `764.89` | `781.56` | `+2.18%` |
| `64` | `42.053` | `42.707` | `+1.56%` | `1436.96` | `1450.09` | `+0.91%` |

### `Qwen/Qwen3-0.6B`, `1024 / 4`, non-stream

| Concurrency | Runner req/s | Myelon req/s | Req/s delta | Runner TTFT ms | Myelon TTFT ms | TTFT delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1` | `9.733` | `8.474` | `-12.94%` | `102.71` | `117.97` | `+14.86%` |
| `2` | `13.727` | `12.489` | `-9.02%` | `145.59` | `160.08` | `+9.95%` |
| `4` | `20.642` | `20.915` | `+1.32%` | `193.69` | `190.99` | `-1.39%` |
| `8` | `28.343` | `30.134` | `+6.32%` | `282.09` | `265.24` | `-5.97%` |
| `16` | `36.104` | `37.002` | `+2.49%` | `442.63` | `431.61` | `-2.49%` |
| `32` | `39.634` | `41.389` | `+4.43%` | `805.78` | `771.42` | `-4.26%` |
| `64` | `43.532` | `41.405` | `-4.89%` | `1464.04` | `1540.58` | `+5.23%` |

## Read

- The extension did find a stronger server-side Myelon window than the original `1024 / 16` Phase A slice.
- That stronger window appears only on the smaller model and very low decode:
  - best point is `Qwen/Qwen3-0.6B`, `1024 / 1`, `c16`
  - `+11.99%` requests/sec
  - `-10.46%` TTFT
- `Qwen/Qwen3-4B`, `1024 / 4` also shows a consistent but modest low-to-mid concurrency window:
  - best point `c4`: `+5.77%` requests/sec, `-5.43%` TTFT
- `Qwen/Qwen3-4B`, `1024 / 1` is mostly flat to negative.
- `Qwen/Qwen3-0.6B`, `1024 / 4` is highly shape-sensitive:
  - negative at `c1` and `c2`
  - positive at `c8`, `c16`, and `c32`

## Conclusion

Extended Phase A improves the original server-side read, but not enough to change the overall decision.

- Myelon can show a larger server-side gain than the first `1024 / 16` Phase A slice suggested.
- That gain is still narrow, model-sensitive, and concurrency-sensitive.
- The best retained point is still nowhere near a large `x`-factor serving story.
- Phase B remains blocked by default on the active `2 x H100` host.

## Primary Artifacts

- CSV matrix: [extended_phase_a_qwen3_tp2_fixed_prompt_results.csv](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/extended_phase_a_qwen3_tp2_fixed_prompt_results.csv)
- 4B raw run roots:
  - [qwen3_4b_tp2_random_1024_1_nostream_extended](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/qwen3_4b_tp2_random_1024_1_nostream_extended)
  - [qwen3_4b_tp2_random_1024_4_nostream_extended](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/qwen3_4b_tp2_random_1024_4_nostream_extended)
- 0.6B raw run roots:
  - [qwen3_06b_tp2_random_1024_1_nostream_extended](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/qwen3_06b_tp2_random_1024_1_nostream_extended)
  - [qwen3_06b_tp2_random_1024_4_nostream_extended](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/qwen3_06b_tp2_random_1024_4_nostream_extended)
