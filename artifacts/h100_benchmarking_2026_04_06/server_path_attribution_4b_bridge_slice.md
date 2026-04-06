# H100 `Qwen3-4B` Bridge Pair And Server-Path Attribution Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Branch: `myelon-integration-1`

## Purpose

Lock the first clean `Qwen/Qwen3-4B` same-host `tp2` bridge/control pair on H100 and add retained server-path attribution so later analysis does not depend on reopening raw logs manually.

## What Changed

- retained `report.json` files are now normalized before being written, not only the derived `reports/` bundle
- retained summaries now carry:
  - `observed_server_path_attribution`
  - prefill totals and mean prefill throughput
  - prompt/decode totals and mean prompt/decode throughput
  - prefix-cache hit counts
  - swap-out attempt counts
  - dropped-request counts
  - stream-generation-failure counts

## Validation

```bash
cd /root/Documents/myelon-launch/vllm.rs
python3 -m unittest discover -s scripts/tests -v
python3 -m py_compile \
  scripts/myelon_report_common.py \
  scripts/myelon_validation_common.py \
  scripts/run_myelon_benchmark_matrix.py \
  scripts/run_myelon_server_benchmark_matrix.py \
  scripts/run_myelon_pd_benchmark_matrix.py \
  scripts/tests/test_benchmark_contract.py
```

## Retained Pair

### Hard Thrash

Artifact:

- `artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v1`

Result:

- runner: `1.030 req/s`, `16483.27 ms` TTFT, `26775.38 ms` latency
- myelon: `1.069 req/s`, `15416.27 ms` TTFT, `25802.89 ms` latency
- delta: `+3.79% req/s`, `-6.47%` TTFT, `-3.63%` latency

Attribution signals:

- both legs reached real GPU KV pressure:
  - runner `94.4%`
  - myelon `95.2%`
- only Myelon engaged CPU swap:
  - runner `0.0%`
  - myelon `84.8%`
- both legs attempted swap-out once
- runner dropped one request; Myelon dropped none
- runner had `34` successes / `3` failures / `6` HTTP `422`
- myelon had `33` successes / `4` failures / `8` HTTP `422`
- prefill totals still favored Myelon:
  - runner `468.41s` total prefill, `503.91 tok/s` mean prefill throughput
  - myelon `411.47s` total prefill, `546.01 tok/s` mean prefill throughput

Read:

- this is a real bridge win, not a pure artifact
- the win is still low-single-digit because the server path is now sharing the story with swap, admission churn, and decode

### Shared-Prefix Control

Artifact:

- `artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v1`

Result:

- runner: `1.437 req/s`, `4842.78 ms` TTFT, `21564.46 ms` latency
- myelon: `1.438 req/s`, `4827.47 ms` TTFT, `21637.49 ms` latency
- delta: `+0.07% req/s`, `-0.32%` TTFT, `+0.34%` latency

Attribution signals:

- no failures or HTTP `422` on either leg
- no swap or dropped requests on either leg
- both legs stayed at moderate GPU pressure:
  - runner `38.6%`
  - myelon `38.6%`
- both legs saw the same shared-prefix reuse shape:
  - `128` prefix-cache hits
  - `160` successful requests
- Myelon still showed better prompt-side totals, but the control stayed effectively neutral end to end:
  - runner `805.17s` total prompt, `1655.10 tok/s`
  - myelon `774.38s` total prompt, `1790.54 tok/s`

Read:

- this is the clean control we wanted
- it supports the claim that the positive `4B` thrash result is tied to pressure shape, not just uncontrolled model drift

## Current Conclusion

The `4B` bridge pair narrows the open question cleanly:

- cache-hostile serving on the full server path can produce a real Myelon gain
- that gain is still far smaller than the CLI `prefill_stress` win
- the compression is now attributable to scheduler/admission/swap behavior and not just a missing transport-path measurement

## Next Step

Use these attribution fields to explain the existing `30B-A3B` bridge results before starting another blind server-prefill parameter sweep.
