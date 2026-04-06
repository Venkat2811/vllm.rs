# H100 CLI Prefill Stop-Point Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Model: `Qwen/Qwen3-30B-A3B`
Topology: `tp2`

## Summary

The CLI `prefill_stress` harness now treats planned stop-point probes as completed retained evidence instead of lumping them into generic `partial` status. That was the missing semantic layer for the H100 `Qwen3-30B-A3B` TP=2 campaign.

This slice also retained three useful benchmark boundaries:

- `first_prefill_completion`
- `minimal_decode_completion`
- warmup failure on the known `batch=256` decode cliff

## Retained Runs

- `artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1`
- `artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch128_v1`
- `artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch256_v2`

Rollups:

- `artifacts/h100_prefill_campaign_20260406/reports/benchmarks/current_findings.md`
- `artifacts/h100_prefill_campaign_20260406/reports/benchmarks/high_level_summary.md`
- `artifacts/h100_prefill_campaign_20260406/reports/benchmarks/per_model_side_by_side.md`

## Main Read

`first_prefill_completion` (`batch=256`):

- runner: `2.42s`, `7.022` first-prefill t/s
- Myelon: `2.42s`, `7.03` first-prefill t/s
- effectively flat on this retained probe

`minimal_decode_completion` (`batch=128`):

- first-prefill seconds: `1.48 -> 1.36` (`-8.11%`)
- prompt t/s: `1401.14 -> 1504.67` (`+7.39%`)
- decode t/s: `1939.38 -> 2024.07` (`+4.37%`)

`minimal_decode_completion` (`batch=256`):

- runner still fails during warmup decode
- retained error:
  - `CUDA_ERROR_INVALID_VALUE`
  - `Runner decode error`
  - engine loop ends with `Runner step error, no response!`
- this remains a real runtime boundary, not a harness parsing bug

## Conclusion

The CLI prefill lane is now semantically correct and reportable:

- first-prefill probes can be retained honestly
- minimal-decode probes can be retained honestly
- stop-point-limited runs now show as completed evidence within their boundary

Current H100 evidence on `Qwen3-30B-A3B` is mixed but useful:

- the retained `batch=128` minimal-decode lane is a real Myelon win
- the retained `batch=256` first-prefill lane is flat
- the retained `batch=256` minimal-decode lane still hits the known decode cliff on the runner baseline

So the open question is no longer whether the CLI harness can express the old transport-sensitive question. It can. The next question is why the strongest current retained H100 TP=2 result sits at the `batch=128` boundary instead of carrying cleanly into `batch=256`.
