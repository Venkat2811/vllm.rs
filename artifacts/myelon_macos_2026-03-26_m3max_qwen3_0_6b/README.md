# Myelon macOS validation artifacts

Date: 2026-03-26
Host: Apple M3 Max MacBook Pro, 96 GB RAM
Repo: vllm.rs
Branch: myelon-integration-1
Model: Qwen/Qwen3-0.6B (local Hugging Face snapshot)
Build features: metal,myelon

Artifacts:
- `ab_report.json`: single-shard A/B run covering direct, forced runner, and myelon modes
- `recovery_report.json`: 3-iteration repeat-run recovery validation in myelon mode

Observed result:
- direct / runner / myelon all exited 0
- all responses matched across A/B cases
- recovery validation passed 3/3 iterations with expected runner mode `process`
- myelon state and shutdown markers were present on all recovery iterations

Local integration fix applied on this host:
- `Cargo.toml` path dependency for `myelon-playground` was corrected from `../../myelon-playground/...` to `../myelon-playground/...` to match the current repo layout under `myelon-launch`
