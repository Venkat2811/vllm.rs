#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

model_path="${VLLM_MODEL_PATH:-/home/venkat/.cache/huggingface/hub/models--Qwen--Qwen1.5-0.5B-Chat-GPTQ-Int4/snapshots/0e58dd1739f12892fd7b2fe0c88245afa423f3fe}"
prompt="${VLLM_PROMPT:-Say hello in one short sentence.}"
max_model_len="${VLLM_MAX_MODEL_LEN:-256}"
max_tokens="${VLLM_MAX_TOKENS:-4}"
seed="${VLLM_SEED:-123}"
timeout_seconds="${VLLM_TIMEOUT_SECONDS:-60}"

if [[ ! -d "${model_path}" ]]; then
    echo "model path does not exist: ${model_path}" >&2
    exit 1
fi

build_features="${VLLM_BUILD_FEATURES:-cuda,myelon}"
echo "==> building vllm-rs and runner with features: ${build_features}"
cargo build --bin vllm-rs --bin runner --features "${build_features}"

common_args=(
    --w "${model_path}"
    --max-num-seqs 1
    --max-model-len "${max_model_len}"
    --max-tokens "${max_tokens}"
    --prompts "${prompt}"
    --dtype bf16
    --seed "${seed}"
)

run_case() {
    local label="$1"
    shift
    echo
    echo "==> ${label}"
    echo "command: timeout ${timeout_seconds} ./target/debug/vllm-rs ${common_args[*]} $*"
    timeout "${timeout_seconds}" ./target/debug/vllm-rs "${common_args[@]}" "$@"
}

run_case "direct path"
run_case "forced subprocess runner" --force-runner
run_case "forced subprocess runner with Myelon IPC" --myelon-ipc
