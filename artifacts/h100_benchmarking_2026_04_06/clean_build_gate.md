# H100 Clean Build Gate

Date: 2026-04-06
Host: `plain-bear-unfolds-fin-02`
Repo: `vllm.rs`
Build target SHA: `e295a8ecbd21fd047a50b8c5368d18d7f3742f99`

## Purpose

Record the clean-build gate required before the next retained H100 benchmark wave.

## Command

```bash
cargo clean
CUDA_COMPUTE_CAP=90 cargo build --release --bin vllm-rs --bin runner --features cuda,nccl,myelon
```

## Result

- status: success
- release build completed on the active H100 host
- elapsed: `1:19.49`
- peak RSS: `2012788 KB`

## Raw Log

- `artifacts/h100_benchmarking_2026_04_06/build_logs/vllm_rs_clean_build.log`

## Notes

- this build gate is the benchmark baseline after crossing B300 `sm_100f`, Blackwell `sm_120f`, and now H100 `sm_90`
- retained H100 benchmark evidence after this point should reference this clean-build gate instead of older carried binaries
