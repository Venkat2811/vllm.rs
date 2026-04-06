# Result Boundary And Shared-Prefix Checkpoint

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`

## Slice

Retained rollups now classify a higher-level `result_boundary` in addition to raw
`status`.

Current bundles and rollups can now distinguish:

- `benchmark_complete`
- `architecture_limited`
- `topology_limited`
- `transport_limited`
- `runtime_limited`

Campaign summaries now emit boundary counts beside status counts.

## Shared-prefix control

The strengthened shared-prefix control already exists on the same H100 host class and
same `32 / 64 / 384` bridge shape as the heavier cache-thrash lane:

- run: `qwen30ba3b_tp2_server_shared_prefix_rr_control_v3`
- profile: `bounded_prefix`
- observed level: `moderate_gpu_pressure`
- runner: `0.535 req/s`
- Myelon: `0.523 req/s`
- requests/sec delta: `-2.24%`
- TTFT delta: `+0.30%`
- latency delta: `+2.71%`

## Read

The bridge lane now has a fair same-host control/result pair:

- `shared_prefix_round_robin_control`: slight regression
- `cache_thrash_round_robin`: modest positive at real GPU-KV pressure

That narrows the next step cleanly: server-path attribution is now more valuable than
more debate about whether the shared-prefix control exists.
