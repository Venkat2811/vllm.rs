# H100 TP-Scale Overlay Contract Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`

## Summary

Retained benchmark contracts, manifests, summaries, and rollups now carry explicit TP-scale metadata instead of hiding it in filenames or shell history.

Added fields:

- `tp_scale_overlay`
- `prefill_tp_size`
- `decode_tp_size`
- `pd_enabled`
- `pd_role_layout`

## Why This Matters

The current machine is only `2 x H100`, but the benchmark taxonomy now needs to scale cleanly to future:

- `tp4`
- `tp8`
- `pd(tp2/tp2)`
- `pd(tp4/tp4)`
- asymmetric PD or TP overlays

This slice makes those overlays part of the retained contract now instead of waiting for the bigger host.

## Retained Proof

The current H100 CLI prefill campaign was backfilled with the new metadata:

- `artifacts/h100_prefill_campaign_20260406/reports/benchmarks/rollup_run_index.md`
- `artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch128_v1/report_reports/reports/manifest.md`
- `artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch128_v1/report_reports/reports/benchmarks/run_summary.md`

Example values on the current host:

- `topology_overlay = tp2`
- `tp_scale_overlay = tp2`
- `prefill_tp_size = 2`
- `decode_tp_size = 2`
- `pd_enabled = false`

## Conclusion

Future multi-GPU scaling work is now a benchmark-execution problem, not a metadata-taxonomy problem. The retained contract can already express the current `2 x GPU` overlays and the future `4x/8x` overlays consistently.
