#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

from myelon_benchmark_common import build_command, run_case
from myelon_validation_common import (
    default_build_features,
    env_str,
    parse_device_ids,
    validate_requested_topology,
)
def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return float(value)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    model_path = env_str(
        "VLLM_MODEL_PATH",
        "/home/venkat/.cache/huggingface/hub/models--Qwen--Qwen1.5-0.5B-Chat-GPTQ-Int4/snapshots/0e58dd1739f12892fd7b2fe0c88245afa423f3fe",
    )
    prompt = env_str("VLLM_PROMPT", "Say hello in one short sentence.")
    max_model_len = env_str("VLLM_MAX_MODEL_LEN", "256")
    max_tokens = env_str("VLLM_MAX_TOKENS", "4")
    seed = env_str("VLLM_SEED", "123")
    num_shards = env_str("VLLM_NUM_SHARDS", "1")
    parsed_num_shards = int(num_shards)
    device_ids = os.environ.get("VLLM_DEVICE_IDS")
    parsed_device_ids = parse_device_ids(device_ids)
    myelon_rpc_depth = os.environ.get("VLLM_MYELON_RPC_DEPTH")
    myelon_response_depth = os.environ.get("VLLM_MYELON_RESPONSE_DEPTH")
    myelon_busy_spin = env_str("VLLM_MYELON_BUSY_SPIN", "0").lower() in {
        "1",
        "true",
        "yes",
    }
    timeout_seconds = int(env_str("VLLM_TIMEOUT_SECONDS", "60"))
    build_features = env_str("VLLM_BUILD_FEATURES", "cuda,myelon")
    max_myelon_prompt_ratio = env_float("VLLM_MAX_MYELON_PROMPT_RATIO", 4.0)
    if "VLLM_BUILD_FEATURES" not in os.environ:
        build_features = default_build_features()
    output_path = Path(
        env_str("VLLM_AB_REPORT_OUT", str(repo_root / "target" / "myelon_ab_report.json"))
    )

    if not Path(model_path).is_dir():
        print(f"model path does not exist: {model_path}", file=sys.stderr)
        print(
            "set VLLM_MODEL_PATH to a local snapshot directory before running this script",
            file=sys.stderr,
        )
        return 1

    try:
        detected_cuda_device_count = validate_requested_topology(
            parsed_num_shards,
            parsed_device_ids,
            build_features,
        )
    except ValueError as error:
        print(f"invalid requested topology: {error}", file=sys.stderr)
        return 1

    subprocess.run(
        ["cargo", "build", "--bin", "vllm-rs", "--bin", "runner", "--features", build_features],
        cwd=repo_root,
        check=True,
    )

    if parsed_num_shards == 1:
        cases = [
            ("direct", ["--num-shards", num_shards]),
            ("runner", ["--num-shards", num_shards, "--force-runner"]),
            ("myelon", ["--num-shards", num_shards, "--myelon-ipc"]),
        ]
        comparison_scope = "single_shard_correctness_smoke"
        performance_expectation = "no_expected_myelon_gain_single_shard"
    else:
        cases = [
            ("runner", ["--num-shards", num_shards, "--force-runner"]),
            ("myelon", ["--num-shards", num_shards, "--myelon-ipc"]),
        ]
        comparison_scope = "multi_shard_process_ab"
        performance_expectation = "myelon_ab_is_meaningful_multi_shard"

    results = []
    for label, extra_args in cases:
        command = build_command(
            repo_root,
            repo_root / "target" / "debug" / "vllm-rs",
            model_path,
            prompt,
            max_model_len,
            max_tokens,
            seed,
            device_ids,
            myelon_rpc_depth,
            myelon_response_depth,
            myelon_busy_spin,
            extra_args,
        )
        results.append(run_case(repo_root, label, command, timeout_seconds))

    report = {
        "model_path": model_path,
        "prompt": prompt,
        "max_model_len": int(max_model_len),
        "max_tokens": int(max_tokens),
        "seed": int(seed),
        "num_shards": parsed_num_shards,
        "device_ids": device_ids,
        "parsed_device_ids": parsed_device_ids,
        "detected_cuda_device_count": detected_cuda_device_count,
        "myelon_rpc_depth": int(myelon_rpc_depth) if myelon_rpc_depth else None,
        "myelon_response_depth": int(myelon_response_depth)
        if myelon_response_depth
        else None,
        "myelon_busy_spin": myelon_busy_spin,
        "max_myelon_prompt_ratio": max_myelon_prompt_ratio,
        "comparison_scope": comparison_scope,
        "performance_expectation": performance_expectation,
        "direct_case_included": parsed_num_shards == 1,
        "build_features": build_features,
        "results": results,
    }

    baseline_response = results[0]["metrics"]["response"]
    report["all_responses_match"] = all(
        result["metrics"]["response"] == baseline_response for result in results
    )

    results_by_label = {result["label"]: result for result in results}
    runner_prompt_seconds = results_by_label["runner"]["metrics"]["prompt_seconds"]
    myelon_prompt_seconds = results_by_label["myelon"]["metrics"]["prompt_seconds"]
    prompt_ratio = None
    if runner_prompt_seconds is not None and myelon_prompt_seconds is not None:
        prompt_ratio = myelon_prompt_seconds / runner_prompt_seconds
    report["myelon_prompt_ratio_vs_runner"] = prompt_ratio

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output_path)

    if any(result["exit_code"] != 0 for result in results):
        return 1
    if not report["all_responses_match"]:
        return 2
    if not results_by_label["myelon"]["metrics"]["myelon_enabled"]:
        return 3
    if prompt_ratio is not None and prompt_ratio > max_myelon_prompt_ratio:
        print(
            (
                "myelon prompt ratio exceeds guardrail: "
                f"{prompt_ratio:.2f} > {max_myelon_prompt_ratio:.2f}"
            ),
            file=sys.stderr,
        )
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
