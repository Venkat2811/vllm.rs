#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

from myelon_benchmark_common import (
    build_command,
    metrics_are_complete,
    run_case_for_stop_point_with_retries,
    summarize_numeric_runs,
)
from myelon_report_common import normalize_report, write_report_bundle
from myelon_validation_common import (
    build_benchmark_contract,
    build_machine_profile,
    classify_model_capability,
    default_build_features,
    env_str,
    infer_cli_run_class,
    parse_device_ids,
    resolve_run_class,
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


def workload_class_for_profile(
    workload_profile: str, prompt_source: str, batch_size: int
) -> str:
    if prompt_source == "custom_env":
        return "custom_prompt_env_burst" if batch_size > 1 else "custom_prompt_env"
    if workload_profile == "synthetic_short":
        return (
            "synthetic_prompt_short_burst"
            if batch_size > 1
            else "synthetic_prompt_short"
        )
    if workload_profile == "synthetic_long_stress":
        return (
            "synthetic_prompt_long_stress_burst"
            if batch_size > 1
            else "synthetic_prompt_long_stress"
        )
    return "prompt_profile_defined"


def resolve_prefill_stop_point(max_tokens: str) -> str:
    explicit = os.environ.get("VLLM_PREFILL_STRESS_STOP_POINT")
    allowed = {
        "first_prefill_completion",
        "minimal_decode_completion",
        "full_completion",
    }
    if explicit:
        if explicit not in allowed:
            raise ValueError(
                f"unsupported VLLM_PREFILL_STRESS_STOP_POINT '{explicit}'"
            )
        return explicit
    try:
        parsed_max_tokens = int(max_tokens)
    except ValueError as error:
        raise ValueError(f"invalid VLLM_MAX_TOKENS '{max_tokens}'") from error
    if parsed_max_tokens <= 1:
        return "minimal_decode_completion"
    return "full_completion"


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    model_path = env_str(
        "VLLM_MODEL_PATH",
        "/root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c",
    )
    max_model_len = env_str("VLLM_MAX_MODEL_LEN", "1024")
    max_tokens = env_str("VLLM_MAX_TOKENS", "64")
    batch_size = env_int("VLLM_BENCHMARK_BATCH_SIZE", 256)
    try:
        prompt, workload_profile, prompt_source = resolve_workload()
        stop_point = resolve_prefill_stop_point(max_tokens)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
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
    capture_raw_system = env_str("VLLM_CAPTURE_RAW_SYSTEM_INFO", "1").lower() in {
        "1",
        "true",
        "yes",
    }
    run_class = resolve_run_class(
        os.environ.get("VLLM_RUN_CLASS"),
        infer_cli_run_class(measured_runs),
    )
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
    if batch_size <= 0:
        print("batch size must be > 0", file=sys.stderr)
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
    require_response = batch_size <= 1
    benchmark_contract = build_benchmark_contract(
        benchmark_family="prefill_stress",
        benchmark_submode="fixed_prompt_burst",
        question_answered="Does Myelon reduce transport-sensitive prompt and prefill cost?",
        workload_class=workload_class_for_profile(
            workload_profile, prompt_source, batch_size
        ),
        warmup_policy=f"cli_warmup_runs:{warmup_runs}",
        first_turn_measured=True,
        arrival_pattern="prompt_burst_serial_runs",
        concurrency_policy={
            "driver": "cli_batch_burst_repeated_invocation",
            "batch_size": batch_size,
            "warmup_runs": warmup_runs,
            "measured_runs": measured_runs,
            "max_attempts": max_attempts,
            "mode": mode,
            "expected_num_shards": expected_num_shards,
        },
        cache_pressure_profile="unspecified",
        equivalence_group=(
            "fixed_prompt_burst_bridge"
            if workload_profile == "synthetic_short"
            else None
        ),
        topology_overlay=mode,
        tp_scale_overlay=("tp1" if mode == "single_gpu" else "tp2"),
        prefill_tp_size=(1 if mode == "single_gpu" else 2),
        decode_tp_size=(1 if mode == "single_gpu" else 2),
        pd_enabled=False,
        pd_role_layout=None,
        transport_mode="socket_vs_myelon_process_runner",
        run_class=run_class,
        stop_point=stop_point,
        skip_reason=None,
    )
    machine_profile = build_machine_profile(
        detected_cuda_device_count=detected_cuda_device_count,
        effective_device_ids=parsed_device_ids,
    )
    model_capability = classify_model_capability(model_path)

    def write_failure_report(status: str, failed_case: str, failed_run: dict, stop_point: str) -> int:
        failure_contract = dict(benchmark_contract)
        failure_contract["stop_point"] = stop_point
        failure_report = {
            "benchmark_contract": failure_contract,
            "machine_profile": machine_profile,
            "model_capability": model_capability,
            "status": status,
            "mode": mode,
            "workload_profile": workload_profile,
            "prompt_source": prompt_source,
            "failed_case": failed_case,
            "failed_run": failed_run,
        }
        output_root = output_path.parent / f"{output_path.stem}_reports"
        failure_report["report_bundle"] = write_report_bundle(
            output_root=output_root,
            report=failure_report,
            report_path=output_path,
            repo_root=repo_root,
            capture_raw_system=capture_raw_system,
        )
        failure_report = normalize_report(failure_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(failure_report, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return 2 if status.startswith("warmup") else 3

    for label, extra_args in cases:
        case_command = build_command(
            repo_root,
            binary_path,
            model_path,
            prompt,
            batch_size,
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
            warmup = run_case_for_stop_point_with_retries(
                repo_root,
                f"{label}-warmup-{index + 1}",
                case_command,
                timeout_seconds,
                max_attempts,
                retry_sleep_seconds,
                stop_point,
            )
            warmups.append(warmup)
            if warmup["exit_code"] != 0:
                print(f"warmup failed for case {label}", file=sys.stderr)
                return write_failure_report("warmup_failed", label, warmup, "warmup_failure")
            if not metrics_are_complete(
                warmup["metrics"], stop_point, require_response=require_response
            ):
                print(f"warmup produced incomplete metrics for case {label}", file=sys.stderr)
                return write_failure_report(
                    "warmup_incomplete_metrics",
                    label,
                    warmup,
                    "warmup_incomplete_metrics",
                )

        measured = []
        for index in range(measured_runs):
            run = run_case_for_stop_point_with_retries(
                repo_root,
                f"{label}-measured-{index + 1}",
                case_command,
                timeout_seconds,
                max_attempts,
                retry_sleep_seconds,
                stop_point,
            )
            measured.append(run)
            if run["exit_code"] != 0:
                print(f"measured run failed for case {label}", file=sys.stderr)
                return write_failure_report(
                    "measured_failed",
                    label,
                    run,
                    "measured_failure",
                )
            if not metrics_are_complete(
                run["metrics"], stop_point, require_response=require_response
            ):
                print(f"measured run produced incomplete metrics for case {label}", file=sys.stderr)
                return write_failure_report(
                    "measured_incomplete_metrics",
                    label,
                    run,
                    "measured_incomplete_metrics",
                )

        baseline_response = measured[0]["metrics"].get("response")
        all_responses_match = baseline_response is not None and all(
            run["metrics"].get("response") == baseline_response for run in measured
        )
        report_cases.append(
            {
                "label": label,
                "execution_variant": label,
                "stop_point": stop_point,
                "benchmark_exit_code": 0,
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
    cross_case_response_match = True
    if stop_point != "first_prefill_completion":
        cross_case_response_match = (
            cases_by_label["runner"]["sample_response"]
            == cases_by_label["myelon"]["sample_response"]
        )
    report = {
        "benchmark_contract": benchmark_contract,
        "machine_profile": machine_profile,
        "model_capability": model_capability,
        "status": "completed",
        "mode": mode,
        "workload_profile": workload_profile,
        "prompt_source": prompt_source,
        "model_path": model_path,
        "prompt": prompt,
        "prompt_preview": prompt[:160],
        "max_model_len": int(max_model_len),
        "max_tokens": int(max_tokens),
        "batch_size": batch_size,
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
            "myelon_first_prefill_seconds_ratio_vs_runner": compare_ratio(
                {label: case["measured_summary"] for label, case in cases_by_label.items()},
                "runner",
                "myelon",
                "first_prefill_seconds",
            ),
            "myelon_first_prefill_tps_ratio_vs_runner": compare_ratio(
                {label: case["measured_summary"] for label, case in cases_by_label.items()},
                "runner",
                "myelon",
                "first_prefill_tokens_per_second",
            ),
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
            f"stop_point={stop_point}",
            "TTFT and TPOT are not emitted by this binary path yet; use serving benchmarks for those metrics later.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    output_root = output_path.parent / f"{output_path.stem}_reports"
    report["report_bundle"] = write_report_bundle(
        output_root=output_root,
        report=report,
        report_path=output_path,
        repo_root=repo_root,
        capture_raw_system=capture_raw_system,
    )
    report = normalize_report(report)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output_path)

    if stop_point != "first_prefill_completion" and not cross_case_response_match:
        return 4
    if not cases_by_label["myelon"]["measured"][0]["metrics"]["myelon_enabled"]:
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
