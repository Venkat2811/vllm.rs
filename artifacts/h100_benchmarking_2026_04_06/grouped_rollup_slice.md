# H100 Grouped Rollup Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`

## Summary

The retained rollup layer now emits grouped report bundles instead of only one flat campaign view.

New grouped outputs:

- `reports/benchmarks/by_family/<family>/findings.{md,csv}`
- `reports/benchmarks/by_family/<family>/per_model_side_by_side.{md,csv}`
- `reports/benchmarks/by_equivalence/<group>/matched_runs.{md,csv}`
- `reports/benchmarks/by_equivalence/<group>/per_model_side_by_side.{md,csv}`

## Why This Matters

The flat rollups were already useful, but they still made readers scan across unrelated benchmark families to answer simple questions like:

- what happened in `prefill_stress` only?
- what happened in `pd_qos` only?
- how does the fixed-prompt CLI lane compare to the fixed-prompt server bridge lane?

Grouped reports now answer those directly.

## Retained Proof

The new grouped rollups were generated on real H100 campaigns:

- `artifacts/h100_prefill_campaign_20260406/reports/benchmarks/by_family/prefill_stress/`
- `artifacts/h100_quickpass_20260403_req10/reports/benchmarks/by_family/serving_qos/`
- `artifacts/h100_quickpass_20260403_req10/reports/benchmarks/by_family/pd_qos/`
- `artifacts/h100_bridge_campaign_20260406/reports/benchmarks/by_equivalence/fixed_prompt_burst_bridge/`

## Conclusion

The retained report tree now has both:

- campaign-wide summary views
- grouped views for family-specific and equivalence-group-specific analysis

That makes the next H100 rerun wave easier to interpret without manual spreadsheet work.
