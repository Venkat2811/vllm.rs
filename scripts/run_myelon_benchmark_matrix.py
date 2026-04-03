#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

from myelon_benchmark_common import (
    build_command,
    metrics_are_complete,
    run_case,
    run_case_with_retries,
    summarize_numeric_runs,
)
from myelon_validation_common import (
    default_build_features,
    env_str,
    parse_device_ids,
    validate_requested_topology,
)


SHORT_CONTROL_PROMPT = (
    "Explain IPC tradeoffs briefly."
)

LONG_STRESS_PROMPT = (
    "Summarize the tradeoffs between shared-memory IPC and socket-based "
    "message passing for inference engines. " * 40
    + "End with one short conclusion."
)


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def prepare_cases(mode: str, device_ids: str | None) -> list[tuple[str, list[str]]]:
    if mode == "single_gpu":
        return [
            ("runner", ["--num-shards", "1"]),
            ("myelon", ["--num-shards", "1", "--myelon-ipc"]),
        ]
    if mode == "tp2":
        return [
            ("runner", ["--num-shards", "2", "--force-runner"]),
            ("myelon", ["--num-shards", "2", "--myelon-ipc"]),
        ]
    raise ValueError(f"unsupported VLLM_BENCHMARK_MODE '{mode}'")


def compare_ratio(
    summary_by_label: dict[str, dict],
    baseline_label: str,
    variant_label: str,
    metric_name: str,
) -> float | None:
    baseline = summary_by_label[baseline_label].get(metric_name, {}).get("mean")
    variant = summary_by_label[variant_label].get(metric_name, {}).get("mean")
    if baseline in (None, 0) or variant is None:
        return None
    return round(float(variant) / float(baseline), 6)


def resolve_workload() -> tuple[str, str, str]:
    explicit_prompt = os.environ.get("VLLM_PROMPT")
    if explicit_prompt:
        return explicit_prompt, "custom_env", "custom_env"

    profile = env_str("VLLM_WORKLOAD_PROFILE", "synthetic_short")
    if profile == "synthetic_short":
        return SHORT_CONTROL_PROMPT, profile, "builtin"
    if profile == "synthetic_long_stress":
        return LONG_STRESS_PROMPT, profile, "builtin"
    raise ValueError(f"unsupported VLLM_WORKLOAD_PROFILE '{profile}'")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    model_path = env_str(
        "VLLM_MODEL_PATH",
        "/root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c",
    )
    try:
        prompt, workload_profile, prompt_source = resolve_workload()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    max_model_len = env_str("VLLM_MAX_MODEL_LEN", "1024")
    max_tokens = env_str("VLLM_MAX_TOKENS", "64")
    seed = env_str("VLLM_SEED", "123")
    mode = env_str("VLLM_BENCHMARK_MODE", "single_gpu")
    warmup_runs = env_int("VLLM_BENCHMARK_WARMUP_RUNS", 1)
    measured_runs = env_int("VLLM_BENCHMARK_MEASURED_RUNS", 5)
    max_attempts = env_int("VLLM_BENCHMARK_MAX_ATTEMPTS", 3)
    timeout_seconds = env_int("VLLM_TIMEOUT_SECONDS", 300)
    retry_sleep_seconds = float(env_str("VLLM_BENCHMARK_RETRY_SLEEP_SECONDS", "2"))
    build_features = env_str("VLLM_BUILD_FEATURES", "")
    build_profile = env_str("VLLM_BUILD_PROFILE", "release")
    device_ids = os.environ.get("VLLM_DEVICE_IDS")
    parsed_device_ids = parse_device_ids(device_ids)
    myelon_rpc_depth = env_str("VLLM_MYELON_RPC_DEPTH", "8192")
    myelon_response_depth = env_str("VLLM_MYELON_RESPONSE_DEPTH", "8192")
    myelon_busy_spin = env_str("VLLM_MYELON_BUSY_SPIN", "1").lower() in {
        "1",
        "true",
        "yes",
    }
    output_path = Path(
        env_str(
            "VLLM_BENCHMARK_OUT",
            str(repo_root / "target" / f"myelon_benchmark_{mode}.json"),
        )
    )

    if not build_features:
        build_features = default_build_features()
    if not Path(model_path).is_dir():
        print(f"model path does not exist: {model_path}", file=sys.stderr)
        return 1
    if warmup_runs < 0 or measured_runs <= 0:
        print("warmup runs must be >= 0 and measured runs must be > 0", file=sys.stderr)
        return 1
    if max_attempts <= 0:
        print("max attempts must be > 0", file=sys.stderr)
        return 1

    expected_num_shards = 1 if mode == "single_gpu" else 2
    try:
        detected_cuda_device_count = validate_requested_topology(
            expected_num_shards,
            parsed_device_ids,
            build_features,
        )
    except ValueError as error:
        print(f"invalid requested topology: {error}", file=sys.stderr)
        return 1

    subprocess.run(
        [
            "cargo",
            "build",
            f"--{build_profile}",
            "--bin",
            "vllm-rs",
            "--bin",
            "runner",
            "--features",
            build_features,
        ],
        cwd=repo_root,
        check=True,
    )

    binary_path = repo_root / "target" / build_profile / "vllm-rs"
    cases = prepare_cases(mode, device_ids)
    report_cases = []

    for label, extra_args in cases:
        case_command = build_command(
            repo_root,
            binary_path,
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

        warmups = []
        for index in range(warmup_runs):
            warmup = run_case_with_retries(
                repo_root,
                f"{label}-warmup-{index + 1}",
                case_command,
                timeout_seconds,
                max_attempts,
                retry_sleep_seconds,
            )
            warmups.append(warmup)
            if warmup["exit_code"] != 0:
                print(f"warmup failed for case {label}", file=sys.stderr)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(
                        {
                            "mode": mode,
                            "workload_profile": workload_profile,
                            "prompt_source": prompt_source,
                            "status": "warmup_failed",
                            "failed_case": label,
                            "failed_run": warmup,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return 2
            if not metrics_are_complete(warmup["metrics"]):
                print(f"warmup produced incomplete metrics for case {label}", file=sys.stderr)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(
                        {
                            "mode": mode,
                            "workload_profile": workload_profile,
                            "prompt_source": prompt_source,
                            "status": "warmup_incomplete_metrics",
                            "failed_case": label,
                            "failed_run": warmup,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return 2

        measured = []
        for index in range(measured_runs):
            run = run_case_with_retries(
                repo_root,
                f"{label}-measured-{index + 1}",
                case_command,
                timeout_seconds,
                max_attempts,
                retry_sleep_seconds,
            )
            measured.append(run)
            if run["exit_code"] != 0:
                print(f"measured run failed for case {label}", file=sys.stderr)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(
                        {
                            "mode": mode,
                            "workload_profile": workload_profile,
                            "prompt_source": prompt_source,
                            "status": "measured_failed",
                            "failed_case": label,
                            "failed_run": run,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return 3
            if not metrics_are_complete(run["metrics"]):
                print(f"measured run produced incomplete metrics for case {label}", file=sys.stderr)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(
                        {
                            "mode": mode,
                            "workload_profile": workload_profile,
                            "prompt_source": prompt_source,
                            "status": "measured_incomplete_metrics",
                            "failed_case": label,
                            "failed_run": run,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return 3

        baseline_response = measured[0]["metrics"]["response"]
        all_responses_match = all(
            run["metrics"]["response"] == baseline_response for run in measured
        )
        report_cases.append(
            {
                "label": label,
                "command": case_command,
                "warmups": warmups,
                "measured": measured,
                "warmup_summary": summarize_numeric_runs(warmups),
                "measured_summary": summarize_numeric_runs(measured),
                "all_measured_responses_match": all_responses_match,
                "sample_response": baseline_response,
            }
        )

    cases_by_label = {case["label"]: case for case in report_cases}
    cross_case_response_match = (
        cases_by_label["runner"]["sample_response"] == cases_by_label["myelon"]["sample_response"]
    )
    report = {
        "mode": mode,
        "workload_profile": workload_profile,
        "prompt_source": prompt_source,
        "model_path": model_path,
        "prompt": prompt,
        "prompt_preview": prompt[:160],
        "max_model_len": int(max_model_len),
        "max_tokens": int(max_tokens),
        "seed": int(seed),
        "warmup_runs": warmup_runs,
        "measured_runs": measured_runs,
        "max_attempts": max_attempts,
        "retry_sleep_seconds": retry_sleep_seconds,
        "build_features": build_features,
        "build_profile": build_profile,
        "device_ids": device_ids,
        "parsed_device_ids": parsed_device_ids,
        "detected_cuda_device_count": detected_cuda_device_count,
        "myelon_rpc_depth": int(myelon_rpc_depth) if myelon_rpc_depth else None,
        "myelon_response_depth": int(myelon_response_depth)
        if myelon_response_depth
        else None,
        "myelon_busy_spin": myelon_busy_spin,
        "cases": report_cases,
        "all_cross_case_responses_match": cross_case_response_match,
        "comparisons": {
            "myelon_prompt_seconds_ratio_vs_runner": compare_ratio(
                {label: case["measured_summary"] for label, case in cases_by_label.items()},
                "runner",
                "myelon",
                "prompt_seconds",
            ),
            "myelon_prompt_tps_ratio_vs_runner": compare_ratio(
                {label: case["measured_summary"] for label, case in cases_by_label.items()},
                "runner",
                "myelon",
                "prompt_tokens_per_second",
            ),
            "myelon_decode_seconds_ratio_vs_runner": compare_ratio(
                {label: case["measured_summary"] for label, case in cases_by_label.items()},
                "runner",
                "myelon",
                "decode_seconds",
            ),
            "myelon_decode_tps_ratio_vs_runner": compare_ratio(
                {label: case["measured_summary"] for label, case in cases_by_label.items()},
                "runner",
                "myelon",
                "decode_tokens_per_second",
            ),
        },
        "notes": [
            "This harness reuses the existing vllm-rs CLI metric parsing and adds warmup plus repeated measured runs.",
            "TTFT and TPOT are not emitted by this binary path yet; use serving benchmarks for those metrics later.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output_path)

    if not cross_case_response_match:
        return 4
    if not cases_by_label["myelon"]["measured"][0]["metrics"]["myelon_enabled"]:
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
