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
num_shards="${VLLM_NUM_SHARDS:-1}"
device_ids="${VLLM_DEVICE_IDS:-}"
myelon_rpc_depth="${VLLM_MYELON_RPC_DEPTH:-}"
myelon_response_depth="${VLLM_MYELON_RESPONSE_DEPTH:-}"
myelon_busy_spin="${VLLM_MYELON_BUSY_SPIN:-0}"

if [[ ! -d "${model_path}" ]]; then
    echo "model path does not exist: ${model_path}" >&2
    echo "set VLLM_MODEL_PATH to a local snapshot directory before running this script" >&2
    exit 1
fi

if [[ -n "${VLLM_BUILD_FEATURES:-}" ]]; then
    build_features="${VLLM_BUILD_FEATURES}"
elif [[ "$(uname -s)" == "Darwin" ]]; then
    build_features="metal,myelon"
else
    build_features="cuda,myelon"
fi
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
    --num-shards "${num_shards}"
)

if [[ -n "${device_ids}" ]]; then
    common_args+=(--device-ids "${device_ids}")
fi
if [[ -n "${myelon_rpc_depth}" ]]; then
    common_args+=(--myelon-rpc-depth "${myelon_rpc_depth}")
fi
if [[ -n "${myelon_response_depth}" ]]; then
    common_args+=(--myelon-response-depth "${myelon_response_depth}")
fi
if [[ "${myelon_busy_spin}" == "1" || "${myelon_busy_spin}" == "true" ]]; then
    common_args+=(--myelon-busy-spin)
fi

run_case() {
    local label="$1"
    shift
    echo
    echo "==> ${label}"
    echo "command: timeout ${timeout_seconds} ./target/debug/vllm-rs ${common_args[*]} $*"
    timeout "${timeout_seconds}" ./target/debug/vllm-rs "${common_args[@]}" "$@"
}

if [[ "${num_shards}" == "1" ]]; then
    run_case "direct path"
else
    echo
    echo "==> direct path skipped for num_shards=${num_shards}"
fi
run_case "forced subprocess runner" --force-runner
run_case "forced subprocess runner with Myelon IPC" --myelon-ipc
