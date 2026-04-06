# External Python Serving Phase A Plan

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`

## Purpose

Run one narrow external-client serving campaign against the `vllm.rs` server to answer:

- can Myelon show a clearer serving-side gain when the workload is shaped to favor prompt or prefill cost, using a well-known Python serving benchmark rather than the local wrapper stack

This is Phase A only. Stop after retained results and a written reflection.

## Benchmark Client

- [`sglang/benchmark/hicache/bench_serving.py`](/root/Documents/myelon-launch/sglang/benchmark/hicache/bench_serving.py)

Use OpenAI-compatible mode against the `vllm.rs` server.

## Server Pair

Baseline:

- `vllm-rs --server --num-shards 2 --device-ids 0,1 --force-runner`

Myelon:

- `vllm-rs --server --num-shards 2 --device-ids 0,1 --myelon-ipc --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin`

Shared settings:

- no prefix cache
- same model
- same max-model-len
- same max-num-seqs

## Phase A Workload

- model: start with `Qwen/Qwen3-4B`
- topology: `tp2`
- dataset: `random`
- input tokens: `1024`
- output tokens: `16`
- request rate: `inf`
- streaming: disabled
- prefix cache: disabled
- concurrency sweep: `4, 8, 16, 32, 64, 128, 256`

## Escalation Rule

If `Qwen/Qwen3-4B` stays flat and host capacity still allows a fair rerun:

- escalate to `Qwen/Qwen3-30B-A3B`

## Metrics To Retain

- request throughput
- input throughput
- output throughput
- TTFT
- TPOT
- ITL
- end-to-end latency
- concurrency

## Stop Rule

After the Phase A sweep:

- summarize results
- decide whether Phase B is justified
- do not continue directly into `1024 / 100` or ShareGPT without that reflection
