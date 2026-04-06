# H100 Report Manifest Slice

Date: 2026-04-06
Host: `hazy-instance-completes-fin-02`
Scope: retained report bundles and rollups

## What changed

Retained benchmark bundles now write an explicit bundle manifest beside the existing
system snapshot and benchmark summary files.

New files per retained campaign:

- `reports/manifest.json`
- `reports/manifest.md`

The manifest captures:

- benchmark identity
- machine profile
- benchmark contract summary
- transport settings:
  - `build_features`
  - `effective_device_ids`
  - `myelon_rpc_depth`
  - `myelon_response_depth`
  - `myelon_busy_spin`
  - `prefix_cache_enabled`
  - `prefix_cache_max_tokens`
  - `kv_fraction`
  - `cpu_mem_fold`
  - `no_stream`
- paths to the generated report bundle files

## Why it matters

The retained reports are now self-describing enough to answer two questions without
reopening shell history:

1. what was benchmarked
2. what transport and KV-shaping settings were actually active

That is especially important now that server-prefill bridge runs are sensitive to
wait strategy, prefix-cache budget, and KV pressure settings.

## Validation

- `python3 -m unittest discover -s scripts/tests -v`
- `python3 -m py_compile scripts/myelon_report_common.py scripts/tests/test_benchmark_contract.py`

## Next implication

The next rerun wave can be interpreted directly from retained bundles. Missing or
mis-set transport settings should now be obvious from the manifest instead of only
from raw command lines.
