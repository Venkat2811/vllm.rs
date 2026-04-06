#!/usr/bin/env python3
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from myelon_validation_common import (
    build_benchmark_contract,
    build_machine_profile,
    classify_arrival_pattern,
    default_build_features,
    env_str,
    infer_request_run_class,
    infer_workload_class_from_path,
    parse_device_ids,
    resolve_run_class,
    validate_requested_topology,
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RUNTIME_RE = re.compile(r"^runtime_sec = ([0-9.]+)$", re.MULTILINE)
REQUEST_RATE_RE = re.compile(r"^requests_per_sec = ([0-9.]+)$", re.MULTILINE)
WARMUP_RUNTIME_RE = re.compile(r"^warmup_runtime_sec = ([0-9.]+)$", re.MULTILINE)
TOTAL_RUNTIME_RE = re.compile(
    r"^total_runtime_incl_warmup_sec = ([0-9.]+)$", re.MULTILINE
)
AVG_LINE_RE = re.compile(
    r"^\[(ttft_ms|tpot_ms|latency_ms)\s*\]\s+avg:\s+([0-9.]+),\s+min:\s+([0-9.]+),\s+max:\s+([0-9.]+)$",
    re.MULTILINE,
)

SUMMARY_COLUMNS = [
    "count",
    "mean",
    "std",
    "min",
    "25%",
    "50%",
    "75%",
    "90%",
    "99%",
    "max",
]
SUMMARY_METRICS = {
    "ttft_ms",
    "tpot_ms",
    "latency_ms",
    "input_num_turns",
    "input_num_tokens",
    "output_num_tokens",
    "output_num_chunks",
}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes"}


def prepare_cases(mode: str) -> list[tuple[str, list[str]]]:
    if mode == "single_gpu":
        return [
            ("runner", ["--num-shards", "1", "--force-runner"]),
            ("myelon", ["--num-shards", "1", "--myelon-ipc"]),
        ]
    if mode == "tp2":
        return [
            ("runner", ["--num-shards", "2", "--force-runner"]),
            ("myelon", ["--num-shards", "2", "--myelon-ipc"]),
        ]
    raise ValueError(f"unsupported VLLM_SERVER_BENCHMARK_MODE '{mode}'")


def derive_device_ids(
    parsed_device_ids: list[int] | None,
    expected_num_shards: int,
    detected_cuda_device_count: int,
) -> list[int] | None:
    if parsed_device_ids is not None:
        return parsed_device_ids
    if expected_num_shards <= 1:
        return None
    if detected_cuda_device_count < expected_num_shards:
        raise ValueError(
            f"requested {expected_num_shards} shards but only {detected_cuda_device_count} CUDA device(s) are visible"
        )
    return list(range(expected_num_shards))


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def parse_summary(log_text: str) -> dict:
    clean = strip_ansi(log_text)
    summary: dict[str, object] = {
        "runtime_sec": None,
        "requests_per_sec": None,
        "warmup_runtime_sec": None,
        "total_runtime_incl_warmup_sec": None,
        "table": {},
    }

    runtime_match = RUNTIME_RE.search(clean)
    if runtime_match:
        summary["runtime_sec"] = float(runtime_match.group(1))
    request_rate_match = REQUEST_RATE_RE.search(clean)
    if request_rate_match:
        summary["requests_per_sec"] = float(request_rate_match.group(1))
    warmup_match = WARMUP_RUNTIME_RE.search(clean)
    if warmup_match:
        summary["warmup_runtime_sec"] = float(warmup_match.group(1))
    total_runtime_match = TOTAL_RUNTIME_RE.search(clean)
    if total_runtime_match:
        summary["total_runtime_incl_warmup_sec"] = float(total_runtime_match.group(1))

    table: dict[str, dict[str, float]] = {}
    for raw_line in clean.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        metric_name = fields[0]
        if metric_name not in SUMMARY_METRICS or len(fields) < len(SUMMARY_COLUMNS) + 1:
            continue
        values = {}
        for column, raw_value in zip(SUMMARY_COLUMNS, fields[1 : len(SUMMARY_COLUMNS) + 1]):
            try:
                values[column] = float(raw_value)
            except ValueError:
                break
        if len(values) == len(SUMMARY_COLUMNS):
            table[metric_name] = values
    for match in AVG_LINE_RE.finditer(clean):
        metric_name = match.group(1)
        if metric_name not in table:
            table[metric_name] = {
                "mean": float(match.group(2)),
                "min": float(match.group(3)),
                "max": float(match.group(4)),
            }
    summary["table"] = table
    return summary


def wait_for_server_ready(base_url: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    models_url = f"{base_url}/v1/models"
    last_error: str | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(models_url, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
                models = payload.get("data", [])
                if not models:
                    raise RuntimeError("server returned no models")
                return payload
        except (
            RuntimeError,
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ) as error:
            last_error = str(error)
            time.sleep(0.5)

    raise TimeoutError(
        f"timed out waiting for {models_url} after {timeout_seconds}s: {last_error}"
    )


def terminate_process(process: subprocess.Popen[bytes], timeout_seconds: int) -> int:
    if process.poll() is not None:
        return int(process.returncode)

    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout_seconds)
    return int(process.returncode)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    upstream_repo_root = repo_root.parent / "vllm"
    upstream_benchmark_script = (
        upstream_repo_root / "benchmarks" / "multi_turn" / "benchmark_serving_multi_turn.py"
    )
    model_path = env_str(
        "VLLM_MODEL_PATH",
        "/root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c",
    )
    workload_file = Path(
        env_str(
            "VLLM_BENCHMARK_INPUT_FILE",
            str(
                repo_root
                / "artifacts"
                / "b300_benchmarking_2026_04_02"
                / "synthetic_multi_turn_smoke.json"
            ),
        )
    )
    mode = env_str("VLLM_SERVER_BENCHMARK_MODE", "single_gpu")
    max_model_len = env_str("VLLM_MAX_MODEL_LEN", "1024")
    seed = env_str("VLLM_SEED", "123")
    build_profile = env_str("VLLM_BUILD_PROFILE", "release")
    build_features = env_str("VLLM_BUILD_FEATURES", "")
    device_ids = os.environ.get("VLLM_DEVICE_IDS")
    parsed_device_ids = parse_device_ids(device_ids)
    max_num_seqs = env_int("VLLM_SERVER_MAX_NUM_SEQS", 8)
    server_ready_timeout_seconds = env_int("VLLM_SERVER_READY_TIMEOUT_SECONDS", 300)
    benchmark_timeout_seconds = env_int("VLLM_SERVER_BENCH_TIMEOUT_SECONDS", 900)
    request_timeout_seconds = env_int("VLLM_SERVER_REQUEST_TIMEOUT_SECONDS", 180)
    num_clients = env_int("VLLM_SERVER_BENCH_NUM_CLIENTS", 2)
    max_active_conversations = env_int("VLLM_SERVER_BENCH_MAX_ACTIVE_CONVERSATIONS", 4)
    max_num_requests = env_int("VLLM_SERVER_BENCH_MAX_NUM_REQUESTS", 16)
    max_turns = env_int("VLLM_SERVER_BENCH_MAX_TURNS", 4)
    max_retries = env_int("VLLM_SERVER_BENCH_MAX_RETRIES", 1)
    request_rate = env_str("VLLM_SERVER_BENCH_REQUEST_RATE", "0")
    port_base = env_int("VLLM_SERVER_BENCH_PORT_BASE", 18080)
    warmup_step = env_bool("VLLM_SERVER_BENCH_WARMUP_STEP", True)
    no_stream = env_bool("VLLM_SERVER_BENCH_NO_STREAM", False)
    run_class = resolve_run_class(
        os.environ.get("VLLM_RUN_CLASS"),
        infer_request_run_class(max_num_requests if max_num_requests > 0 else None),
    )

    if not build_features:
        build_features = default_build_features()
    if not Path(model_path).is_dir():
        print(f"model path does not exist: {model_path}", file=sys.stderr)
        return 1
    if not workload_file.is_file():
        print(f"workload file does not exist: {workload_file}", file=sys.stderr)
        return 1
    if not upstream_benchmark_script.is_file():
        print(f"upstream benchmark script does not exist: {upstream_benchmark_script}", file=sys.stderr)
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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(
        env_str(
            "VLLM_SERVER_BENCHMARK_OUT_DIR",
            str(
                repo_root
                / "artifacts"
                / "b300_benchmarking_2026_04_02"
                / f"server_benchmark_{mode}_{timestamp}"
            ),
        )
    )
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "report.json"

    report: dict[str, object] = {
        "mode": mode,
        "model_path": model_path,
        "workload_file": str(workload_file),
        "build_profile": build_profile,
        "build_features": build_features,
        "device_ids": device_ids,
        "parsed_device_ids": parsed_device_ids,
        "detected_cuda_device_count": detected_cuda_device_count,
        "max_model_len": int(max_model_len),
        "max_num_seqs": max_num_seqs,
        "seed": int(seed),
        "num_clients": num_clients,
        "max_active_conversations": max_active_conversations,
        "max_num_requests": max_num_requests if max_num_requests > 0 else None,
        "max_turns": max_turns,
        "max_retries": max_retries,
        "request_rate": float(request_rate),
        "warmup_step": warmup_step,
        "no_stream": no_stream,
        "server_ready_timeout_seconds": server_ready_timeout_seconds,
        "benchmark_timeout_seconds": benchmark_timeout_seconds,
        "request_timeout_seconds": request_timeout_seconds,
        "cases": [],
    }

    base_env = os.environ.copy()
    compute_cap_override = os.environ.get("CUDA_COMPUTE_CAP")
    if compute_cap_override:
        base_env.setdefault("CUDA_COMPUTE_CAP", compute_cap_override)
    base_env.setdefault(
        "KEEP_ALIVE_INTERVAL",
        env_str("VLLM_SERVER_KEEP_ALIVE_INTERVAL", "0"),
    )

    try:
        cases = prepare_cases(mode)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    try:
        effective_device_ids = derive_device_ids(
            parsed_device_ids,
            expected_num_shards,
            detected_cuda_device_count,
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    effective_device_ids_str = (
        ",".join(str(device_id) for device_id in effective_device_ids)
        if effective_device_ids is not None
        else None
    )
    workload_class = infer_workload_class_from_path(str(workload_file))
    warmup_policy = (
        "warmup_step_skips_first_turn" if warmup_step else "measure_first_turn"
    )
    benchmark_contract = build_benchmark_contract(
        benchmark_family="serving_qos",
        question_answered="What user-facing QoS difference does Myelon produce in persistent serving?",
        workload_class=workload_class,
        warmup_policy=warmup_policy,
        first_turn_measured=not warmup_step,
        arrival_pattern=classify_arrival_pattern(request_rate),
        concurrency_policy={
            "driver": "persistent_http_server",
            "max_num_seqs": max_num_seqs,
            "num_clients": num_clients,
            "max_active_conversations": max_active_conversations,
            "max_num_requests": max_num_requests if max_num_requests > 0 else None,
            "max_turns": max_turns,
            "request_rate": float(request_rate),
            "mode": mode,
        },
        run_class=run_class,
        stop_point="full_completion",
        skip_reason=None,
    )
    machine_profile = build_machine_profile(
        detected_cuda_device_count=detected_cuda_device_count,
        effective_device_ids=effective_device_ids,
    )
    report["effective_device_ids"] = effective_device_ids
    report["benchmark_contract"] = benchmark_contract
    report["machine_profile"] = machine_profile

    for index, (label, topology_args) in enumerate(cases):
        port = port_base + index
        case_dir = output_root / label
        case_dir.mkdir(parents=True, exist_ok=True)
        server_log_path = case_dir / "server.log"
        benchmark_log_path = case_dir / "benchmark.log"
        benchmark_output_path = case_dir / "conversations.json"
        base_url = f"http://127.0.0.1:{port}"

        server_command = [
            str(binary_path),
            "--server",
            "--port",
            str(port),
            "--w",
            model_path,
            "--max-model-len",
            max_model_len,
            "--max-num-seqs",
            str(max_num_seqs),
            "--dtype",
            "bf16",
            "--seed",
            seed,
            *topology_args,
        ]
        if effective_device_ids_str:
            server_command.extend(["--device-ids", effective_device_ids_str])

        benchmark_command = [
            "uv",
            "run",
            "--with",
            "aiohttp",
            "--with",
            "numpy",
            "--with",
            "pandas",
            "--with",
            "transformers",
            "--with",
            "tqdm",
            "python3",
            str(upstream_benchmark_script),
            "--input-file",
            str(workload_file),
            "--output-file",
            str(benchmark_output_path),
            "--model",
            model_path,
            "--url",
            base_url,
            "--num-clients",
            str(num_clients),
            "--max-active-conversations",
            str(max_active_conversations),
            "--max-turns",
            str(max_turns),
            "--max-retries",
            str(max_retries),
            "--request-timeout-sec",
            str(request_timeout_seconds),
            "--request-rate",
            request_rate,
        ]
        if max_num_requests > 0:
            benchmark_command.extend(
                [
                    "--max-num-requests",
                    str(max_num_requests),
                ]
            )
        if warmup_step:
            benchmark_command.append("--warmup-step")
        if no_stream:
            benchmark_command.append("--no-stream")

        case_report: dict[str, object] = {
            "label": label,
            "execution_variant": label,
            "stop_point": "full_completion",
            "skip_reason": None,
            "server_port": port,
            "server_command": server_command,
            "benchmark_command": benchmark_command,
            "server_log_path": str(server_log_path),
            "benchmark_log_path": str(benchmark_log_path),
            "benchmark_output_path": str(benchmark_output_path),
        }

        with server_log_path.open("wb") as server_log:
            server = subprocess.Popen(
                server_command,
                cwd=repo_root,
                stdout=server_log,
                stderr=subprocess.STDOUT,
                env=base_env,
            )

        try:
            ready_payload = wait_for_server_ready(base_url, server_ready_timeout_seconds)
            models = ready_payload.get("data", [])
            served_model_name = models[0]["id"]
            case_report["served_model_name"] = served_model_name

            benchmark_command_with_model = list(benchmark_command)
            benchmark_command_with_model.extend(["--served-model-name", served_model_name])
            case_report["benchmark_command"] = benchmark_command_with_model

            started_at = time.time()
            completed = subprocess.run(
                benchmark_command_with_model,
                cwd=repo_root,
                env=base_env,
                capture_output=True,
                text=True,
                timeout=benchmark_timeout_seconds,
                check=False,
            )
            finished_at = time.time()

            benchmark_text = completed.stdout
            if completed.stderr:
                benchmark_text = benchmark_text + "\n" + completed.stderr
            benchmark_log_path.write_text(benchmark_text, encoding="utf-8")

            case_report["benchmark_exit_code"] = completed.returncode
            case_report["benchmark_elapsed_seconds"] = round(finished_at - started_at, 3)
            case_report["summary"] = parse_summary(benchmark_text)
        except subprocess.TimeoutExpired as error:
            case_report["benchmark_timeout"] = benchmark_timeout_seconds
            case_report["benchmark_exit_code"] = None
            case_report["stop_point"] = "benchmark_timeout"
            benchmark_log_path.write_text(
                f"benchmark timed out after {benchmark_timeout_seconds}s\n{error}\n",
                encoding="utf-8",
            )
        except Exception as error:  # noqa: BLE001
            case_report["benchmark_exit_code"] = None
            case_report["stop_point"] = "runtime_error_boundary"
            case_report["error"] = str(error)
        finally:
            case_report["server_exit_code"] = terminate_process(server, 10)

        report["cases"].append(case_report)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
