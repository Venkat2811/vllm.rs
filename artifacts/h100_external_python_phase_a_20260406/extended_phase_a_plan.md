# Extended Phase A Plan

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Status: complete

## Reason

The first external Python serving Phase A showed:

- real Myelon gains through the HTTP server path
- only single-digit wins at low concurrency
- parity at saturation

This extension is still no-code and still Phase A. It exists only to test whether a more prompt-dominant server shape can expose a stronger Myelon gain before any realism-oriented Phase B work.

## Narrow Extension Scope

Keep the same client and server surface:

- client: `scripts/benchmark_server_fixed_prompt_burst.py`
- server: `vllm.rs` OpenAI-compatible chat server
- topology: `tp2`
- prefix cache disabled
- non-streaming

Change only:

- model set:
  - `Qwen/Qwen3-4B`
  - `Qwen/Qwen3-0.6B`
- output caps:
  - `1`
  - `4`
- concurrency sweep:
  - `1, 2, 4, 8, 16, 32, 64`

Prompt stays fixed at roughly `1024` tokens.

## Goal

Find the highest-signal no-code server-side regime on the current `2 x H100` host.

## Stop Rule

Stop after these targeted extended Phase A runs are retained and summarized.

Do not auto-open:

- streaming
- `1024 / 100`
- ShareGPT
- multiturn

unless the retained extended Phase A read explicitly justifies it.

## Outcome

The extension completed all four targeted slices:

- `Qwen/Qwen3-4B`, `1024 / 1`, `c1..64`
- `Qwen/Qwen3-4B`, `1024 / 4`, `c1..64`
- `Qwen/Qwen3-0.6B`, `1024 / 1`, `c1..64`
- `Qwen/Qwen3-0.6B`, `1024 / 4`, `c1..64`

Best retained point:

- `Qwen/Qwen3-0.6B`, `1024 / 1`, `c16`
- `35.184 -> 39.402 req/s` (`+11.99%`)
- `442.08 -> 395.85 ms` TTFT (`-10.46%`)

Overall read:

- lower decode and the smaller model do expose a stronger server-side Myelon window than the original `1024 / 16` Phase A slice
- but the gain is still narrow and nowhere near the old CLI `prefill_stress` multiplier
- extended Phase A does not justify auto-opening Phase B on this host

Primary retained summary:

- [extended_phase_a_qwen3_tp2_fixed_prompt_summary.md](/root/Documents/myelon-launch/vllm.rs/artifacts/h100_external_python_phase_a_20260406/extended_phase_a_qwen3_tp2_fixed_prompt_summary.md)
