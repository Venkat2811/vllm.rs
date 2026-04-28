# Myelon Mode Selection Guide

**Last updated:** 2026-04-28 — based on Mac M3 Max long-ctx PD campaign (A1-A9), 4× H200 RFC 0033 campaign, 2× H200 RFC 0038 campaign (Phases A/B/C/D/E), and Mac multi-turn RFC 0037 campaign (Matrix S + Matrix P).

This doc tells you WHEN to enable Myelon engine↔runner IPC and KV transport vs. when to leave them off. Default is **off** until empirically justified per workload.

## TL;DR

**Myelon helps when transport is the bottleneck. Outside that regime, it ties or regresses.**

## Mode matrix

vllm.rs exposes two orthogonal Myelon controls (will collapse to a single `--myelon-mode={off,ipc,kv,both}` after the cleanup PR; see TODO):

- `--myelon-ipc` toggles **engine↔runner Myelon-IPC** (vs TCP socket runner)
- `--pd-url myelon://...` toggles **PD KV transport** (vs `tcp://...` or `file://...` for CUDA-IPC)

## Recommended mode by workload

### ✅ Use Myelon engine↔runner IPC + KV transport (`--myelon-ipc --myelon-access-mode typed --pd-url myelon://...`)

| workload | Mac/Apple M-series | NVIDIA H200/A100 |
| :------- | :------------------ | :--------------- |
| **PD single-turn long-context (per-request KV ≥ 400 MB)** | **Strongly recommend.** Mac campaign A1-A8 measured +47% to +353% rps wins (4B+4k +137%, 14B+1k +47.9%, 14B+2k +353%, 8B+4k +311%, all vs socket). | Modest +2-3.3% over cuda_ipc at high-concurrency / ctx=8k+ / FP8-KV. Not the default; opt-in for these regimes. |
| HTTP single-turn c=32 moderate-ctx | Recommend. +7-8% rps, −10% ttft p99 on 4B/8B. | Untested; predicted modest win. |
| Multi-turn rounds 1-10, single-process | Recommend (Mac measured +7-8% rps at r=1/5/10). | Predicted similar. |
| **Cross-host PD** | n/a | **Recommend** — cuda_ipc requires same-host CUDA contexts; Myelon-KV works over POSIX SHM. |

### ⚠️ Use Myelon engine↔runner IPC only (no KV transport: `--myelon-ipc` without `--pd-url myelon://`)

| workload | recommendation |
| :------- | :------------- |
| HTTP single-turn small ctx | Wash; either is fine. |
| Multi-turn r ≤ 10 | Recommend (the IPC win still holds at low round counts). |

### ❌ Do NOT use Myelon

| workload | reason |
| :------- | :----- |
| **Multi-turn deep sessions (rounds ≥ 20) PD with `--pd-url myelon://`** | Mac campaign measured **−4.6% rps + 3-4× ttft p50 inflation** vs PD socket. Mechanism: prefix-cache amortizes per-turn KV transfer to ~39 MB; Myelon SHM ring's per-message overhead (~10 ms frame setup) exceeds TCP loopback's ~0.05 ms syscall cost at this small-payload high-frequency regime. |
| **Big MoE engine↔runner (122B-A10B and similar)** | 2× H200 Phase E measured **−22.4% rps regression** at TP=2 c=8 ctx=1k. Mechanism: MoE expert dispatch generates chatty small-message RPC traffic; Myelon's typed-IPC handles it worse than Linux TCP loopback. |
| Single-turn ctx=1k on fast NVIDIA boxes | 4× H200 RFC 0033 measured **parity ±2%** — transport had ~10× headroom unused; saving from Myelon was below noise. |
| Single-turn ctx=16k+ on NVIDIA at moderate concurrency | 2× H200 Phase D measured **parity ±3%** — prefill compute dominates total request time; transport delta becomes invisible. |

## The mental model

**Per-request (or per-turn) KV bytes determines transport choice on Mac:**

```
per_turn_kv_bytes = bytes_per_token(model) × tokens_to_prefill
                  = bytes_per_token × (prompt_len - cache_hit_len)

if per_turn_kv_bytes >= 400 MB:
    # Bandwidth-bound regime — transport-saturating workload
    → choose Myelon-typed-KV (huge wins, +47% to +353% rps)
elif per_turn_kv_bytes <= 50 MB:
    # Small-message regime — Myelon ring overhead dominates
    → choose socket (Myelon regresses up to 4× ttft p50)
else:
    # 50-400 MB regime — wash, default by deployment ergonomics
    → either is fine; cuda_ipc preferred on NVIDIA when available
```

For per-token KV bytes of common Qwen3 models (BF16, num_kv_heads=8 from GQA, head_dim=128):
- Qwen3-4B / 8B: 36 layers → **144 KB / token**
- Qwen3-14B: 40 layers → **160 KB / token**
- Qwen3-30B-A3B (MoE, 4 KV heads via GQA halving): 48 layers → **96 KB / token** *(less than 14B despite more params — MoE sparsity doesn't affect KV; KV-head count does)*

## H200 ship-decision (RFC 0038 §13 verdict)

`typed_kv` vs `cuda_ipc` on 2× H200 with full NVLink (NV18):
- **Best**: +3.3% (30B ctx=8k c=4)
- **Worst**: −5.6% (30B ctx=4k c=4 BF16, the "killer cell")
- **Ship as non-default option** (within ±5% across 4/5 cells).

Win zone: high-concurrency + moderate context + FP8-KV + cross-host. Default zone: keep CUDA-IPC for single-pair PD on NVLink-class boxes.

## What this guide cannot answer (open questions)

- **Multi-turn PD on NVIDIA** — extrapolating Mac findings predicts even worse than parity (faster TCP loopback + same Myelon ring overhead). Not measured directly.
- **Long-context multi-turn** — Mac campaign used 200-tok first-turn prompts. The interaction between long single-turn KV (Myelon wins big) and multi-turn cache amortization (Myelon loses) at 4k+ first-turn + 20 follow-up rounds is unmeasured.
- **PD-TP4-TP4 (split-the-box) on H200/A100** — requires ≥4 GPUs; deferred until that hardware returns.
- **122B-A10B PD** — 122B doesn't fit on 2 GPUs at TP=1+TP=1; requires ≥4 GPUs. The H5 ship-decision for big-MoE PD remains open.

## References

- `ai-chat-exports/.../2_artifacts/2026-04-28_mac_myelon_campaign/` — Mac single-turn long-ctx PD campaign (A1-A9, +137%/+47%/+353%/+311% headlines)
- `ai-chat-exports/.../2_artifacts/2026-04-28_mac_multiturn_campaign/` — Mac multi-turn campaign (Matrix S + Matrix P, H1-H5 verdict)
- `ai-chat-exports/.../2_artifacts/2026-04-28_h200_2gpu_myelon_campaign/` — 2× H200 4-cell ship-decision matrix + Phase D (16k/32k/64k) + Phase E (122B-A10B)
- `ai-chat-exports/.../2_artifacts/2026-04-27_h200_myelon_campaign/` — Original 4× H200 campaign (RFC 0033)
- `ai-chat-exports/.../0_rfcs/0034_typed_end_to_end_myelon_ipc.md` — Typed end-to-end zero-copy design
- `ai-chat-exports/.../0_rfcs/0037_multiturn_bench_for_vllm_rs.md` — Multi-turn campaign plan
- `ai-chat-exports/.../0_rfcs/0038_a100_myelon_campaign.md` — 2× H200 (post-A100 pivot) campaign plan
- `ai-chat-exports/.../0_rfcs/0039_myelon_surface_audit_and_cleanup.md` — Cleanup PR proposal (this PR is part of that)
