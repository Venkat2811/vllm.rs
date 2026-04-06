#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from myelon_report_common import normalize_report, write_report_bundle
from myelon_validation_common import (
    build_benchmark_contract,
    build_machine_profile,
    classify_arrival_pattern,
    classify_model_capability,
    classify_pd_transport_capability,
    classify_pd_topology_capability,
    default_build_features,
    detect_cuda_device_count,
    env_str,
    infer_pd_transport_mode,
    infer_request_run_class,
    infer_workload_class_from_path,
    parse_device_ids,
    resolve_run_class,
)
from run_myelon_server_benchmark_matrix import (
    parse_summary,
    terminate_process,
    wait_for_server_ready,
)


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


def env_optional_bool(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return value.lower() in {"1", "true", "yes"}


def wait_for_pd_server_ready(
    log_path: Path,
    process: subprocess.Popen[bytes],
    timeout_seconds: int,
) -> None:
    deadline = time.time() + timeout_seconds
    ready_markers = (
        "PD server started",
        "waiting for prefill request",
    )

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"PD server exited early with code {process.returncode}")
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            if any(marker in text for marker in ready_markers):
                return
        time.sleep(0.5)

    raise TimeoutError(f"timed out waiting for PD server readiness after {timeout_seconds}s")


def validate_device_roles(
    server_device_ids: list[int] | None,
    client_device_ids: list[int] | None,
) -> None:
    if server_device_ids is None or client_device_ids is None:
        raise ValueError("PD benchmark requires explicit single-device assignments for server and client")
    if len(server_device_ids) != 1 or len(client_device_ids) != 1:
        raise ValueError(
            "PD benchmark currently requires exactly one device id for the PD server "
            "and exactly one device id for the PD client"
        )
    if server_device_ids[0] == client_device_ids[0]:
        raise ValueError("PD server and PD client must use different CUDA devices")

    detected_count = detect_cuda_device_count()
    if detected_count is None:
        return

    invalid_server = [device_id for device_id in server_device_ids if device_id >= detected_count]
    invalid_client = [device_id for device_id in client_device_ids if device_id >= detected_count]
    if invalid_server or invalid_client:
        raise ValueError(
            f"requested PD devices server={server_device_ids}, client={client_device_ids} "
            f"but only {detected_count} CUDA device(s) are visible on this host"
        )


def prepare_cases() -> list[tuple[str, list[str], list[str]]]:
    all_cases = {
        "runner_pd": ("runner_pd", ["--force-runner"], ["--force-runner"]),
        "myelon_pd": ("myelon_pd", ["--myelon-ipc"], ["--myelon-ipc"]),
    }
    selected = env_str("VLLM_PD_CASES", "").strip()
    if not selected:
        return [all_cases["runner_pd"], all_cases["myelon_pd"]]

    cases = []
    for label in [part.strip() for part in selected.split(",") if part.strip()]:
        if label not in all_cases:
            raise ValueError(
                f"unsupported VLLM_PD_CASES entry {label!r}; "
                f"expected one or more of {', '.join(all_cases)}"
            )
        cases.append(all_cases[label])
    return cases


def resolve_pd_benchmark_submode(
    workload_class: str,
    explicit: str | None,
) -> str:
    if workload_class == "pd_first_transfer_control":
        candidate = explicit.strip() if explicit and explicit.strip() else "first_transfer_control"
        if candidate != "first_transfer_control":
            raise ValueError(
                "unsupported pd_qos submode for pd_first_transfer_control workload; "
                "expected 'first_transfer_control'"
            )
        return candidate
    if explicit is not None and explicit.strip():
        candidate = explicit.strip()
    else:
        candidate = "warm_steady_state"
    if candidate not in {"cold_turn", "cold_turn_idle_gap", "warm_steady_state"}:
        raise ValueError(
            f"unsupported pd_qos submode {candidate!r}; "
            "expected one of ['cold_turn', 'cold_turn_idle_gap', 'first_transfer_control', 'warm_steady_state']"
        )
    return candidate


def expected_pd_warmup_step(
    workload_class: str,
    benchmark_submode: str,
) -> bool:
    if workload_class == "pd_first_transfer_control" or benchmark_submode == "first_transfer_control":
        return False
    return benchmark_submode == "warm_steady_state"


def resolve_pd_qos_defaults(benchmark_submode: str) -> dict[str, object]:
    if benchmark_submode == "cold_turn_idle_gap":
        return {
            "num_clients": 1,
            "max_active_conversations": 2,
            "max_num_requests": 16,
            "max_turns": 2,
            "request_rate": "1.0",
        }
    return {
        "num_clients": 1,
        "max_active_conversations": 2,
        "max_num_requests": 16,
        "max_turns": 2,
        "request_rate": "0",
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    upstream_repo_root = repo_root.parent / "vllm"
    upstream_benchmark_script = (
        upstream_repo_root / "benchmarks" / "multi_turn" / "benchmark_serving_multi_turn.py"
    )
    model_path = env_str(
        "VLLM_MODEL_PATH",
        "/root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca",
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
    max_model_len = env_str("VLLM_MAX_MODEL_LEN", "4096")
    seed = env_str("VLLM_SEED", "123")
    build_profile = env_str("VLLM_BUILD_PROFILE", "release")
    build_features = env_str("VLLM_BUILD_FEATURES", "")
    num_clients = env_int("VLLM_SERVER_BENCH_NUM_CLIENTS", 1)
    max_active_conversations = env_int("VLLM_SERVER_BENCH_MAX_ACTIVE_CONVERSATIONS", 2)
    max_num_requests = env_int("VLLM_SERVER_BENCH_MAX_NUM_REQUESTS", 16)
    max_turns = env_int("VLLM_SERVER_BENCH_MAX_TURNS", 2)
    max_retries = env_int("VLLM_SERVER_BENCH_MAX_RETRIES", 1)
    request_rate = env_str("VLLM_SERVER_BENCH_REQUEST_RATE", "0")
    request_timeout_seconds = env_int("VLLM_SERVER_REQUEST_TIMEOUT_SECONDS", 180)
    benchmark_timeout_seconds = env_int("VLLM_SERVER_BENCH_TIMEOUT_SECONDS", 1800)
    server_ready_timeout_seconds = env_int("VLLM_SERVER_READY_TIMEOUT_SECONDS", 300)
    pd_ready_timeout_seconds = env_int("VLLM_PD_READY_TIMEOUT_SECONDS", 300)
    client_port = env_int("VLLM_PD_CLIENT_PORT", 18080)
    max_num_seqs = env_int("VLLM_SERVER_MAX_NUM_SEQS", 8)
    myelon_rpc_depth = env_str("VLLM_MYELON_RPC_DEPTH", "8192")
    myelon_response_depth = env_str("VLLM_MYELON_RESPONSE_DEPTH", "8192")
    myelon_busy_spin = env_str("VLLM_MYELON_BUSY_SPIN", "1").lower() in {
        "1",
        "true",
        "yes",
    }
    no_stream = env_bool("VLLM_SERVER_BENCH_NO_STREAM", False)
    prefix_cache = env_bool("VLLM_PD_PREFIX_CACHE", True)
    capture_raw_system = env_bool("VLLM_CAPTURE_RAW_SYSTEM_INFO", True)
    pd_url = os.environ.get("VLLM_PD_URL")
    run_class = resolve_run_class(
        os.environ.get("VLLM_RUN_CLASS"),
        infer_request_run_class(max_num_requests if max_num_requests > 0 else None),
    )

    server_device_ids_raw = env_str("VLLM_PD_SERVER_DEVICE_IDS", "0")
    client_device_ids_raw = env_str("VLLM_PD_CLIENT_DEVICE_IDS", "1")
    server_device_ids = parse_device_ids(server_device_ids_raw)
    client_device_ids = parse_device_ids(client_device_ids_raw)

    if not build_features:
        build_features = default_build_features()
    if "cuda" not in {feature.strip() for feature in build_features.split(",") if feature.strip()}:
        print("PD benchmark requires CUDA build features", file=sys.stderr)
        return 1
    if not Path(model_path).is_dir():
        print(f"model path does not exist: {model_path}", file=sys.stderr)
        return 1
    if not workload_file.is_file():
        print(f"workload file does not exist: {workload_file}", file=sys.stderr)
        return 1
    if not upstream_benchmark_script.is_file():
        print(f"upstream benchmark script does not exist: {upstream_benchmark_script}", file=sys.stderr)
        return 1

    model_capability = classify_model_capability(model_path)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(
        env_str(
            "VLLM_PD_BENCHMARK_OUT_DIR",
            str(
                repo_root
                / "artifacts"
                / "b300_benchmarking_2026_04_02"
                / f"pd_benchmark_{timestamp}"
            ),
        )
    )
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "report.json"
    workload_class = infer_workload_class_from_path(str(workload_file))
    if workload_class == "file_defined" and "first_transfer" in str(workload_file).lower():
        workload_class = "pd_first_transfer_control"
    try:
        benchmark_submode = resolve_pd_benchmark_submode(
            workload_class,
            os.environ.get("VLLM_PD_BENCHMARK_SUBMODE"),
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    pd_defaults = (
        {}
        if benchmark_submode == "first_transfer_control"
        else resolve_pd_qos_defaults(benchmark_submode)
    )
    num_clients = env_int(
        "VLLM_SERVER_BENCH_NUM_CLIENTS",
        int(pd_defaults.get("num_clients", num_clients)),
    )
    max_active_conversations = env_int(
        "VLLM_SERVER_BENCH_MAX_ACTIVE_CONVERSATIONS",
        int(pd_defaults.get("max_active_conversations", max_active_conversations)),
    )
    max_num_requests = env_int(
        "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS",
        int(pd_defaults.get("max_num_requests", max_num_requests)),
    )
    max_turns = env_int(
        "VLLM_SERVER_BENCH_MAX_TURNS",
        int(pd_defaults.get("max_turns", max_turns)),
    )
    request_rate = env_str(
        "VLLM_SERVER_BENCH_REQUEST_RATE",
        str(pd_defaults.get("request_rate", request_rate)),
    )
    explicit_warmup_step = env_optional_bool("VLLM_SERVER_BENCH_WARMUP_STEP")
    default_warmup_step = expected_pd_warmup_step(workload_class, benchmark_submode)
    if explicit_warmup_step is not None and explicit_warmup_step != default_warmup_step:
        print(
            "VLLM_SERVER_BENCH_WARMUP_STEP conflicts with "
            f"pd_qos.{benchmark_submode}",
            file=sys.stderr,
        )
        return 1
    warmup_step = explicit_warmup_step if explicit_warmup_step is not None else default_warmup_step
    warmup_policy = (
        "warmup_step_skips_first_turn" if warmup_step else "measure_first_turn"
    )
    effective_device_ids = []
    if server_device_ids is not None:
        effective_device_ids.extend(server_device_ids)
    if client_device_ids is not None:
        effective_device_ids.extend(client_device_ids)
    benchmark_contract = build_benchmark_contract(
        benchmark_family="pd_qos",
        benchmark_submode=benchmark_submode,
        question_answered="How does Myelon affect PD-capable serving paths on supported transports and models?",
        workload_class=workload_class,
        warmup_policy=warmup_policy,
        first_turn_measured=not warmup_step,
        arrival_pattern=classify_arrival_pattern(request_rate),
        concurrency_policy={
            "driver": "pd_server_client_http",
            "max_num_seqs": max_num_seqs,
            "num_clients": num_clients,
            "max_active_conversations": max_active_conversations,
            "max_num_requests": max_num_requests if max_num_requests > 0 else None,
            "max_turns": max_turns,
            "request_rate": float(request_rate),
            "server_device_ids": server_device_ids,
            "client_device_ids": client_device_ids,
            "pd_url": pd_url,
        },
        cache_pressure_profile="unspecified",
        equivalence_group=None,
        topology_overlay="pd_tp1",
        transport_mode=infer_pd_transport_mode(pd_url),
        run_class=run_class,
        stop_point="full_completion",
        skip_reason=None,
    )
    detected_cuda_device_count = detect_cuda_device_count()
    topology_capability = classify_pd_topology_capability(
        server_device_ids,
        client_device_ids,
        detected_cuda_device_count,
    )
    transport_capability = classify_pd_transport_capability(
        benchmark_contract["transport_mode"],
        server_device_ids,
        client_device_ids,
    )
    effective_skip_reason = (
        model_capability["pd_skip_reason"]
        or topology_capability["pd_skip_reason"]
        or transport_capability["pd_skip_reason"]
    )
    benchmark_contract["skip_reason"] = effective_skip_reason
    machine_profile = build_machine_profile(
        detected_cuda_device_count=detected_cuda_device_count,
        effective_device_ids=effective_device_ids,
    )

    report: dict[str, object] = {
        "benchmark_contract": benchmark_contract,
        "machine_profile": machine_profile,
        "model_capability": model_capability,
        "topology_capability": topology_capability,
        "transport_capability": transport_capability,
        "model_path": model_path,
        "workload_file": str(workload_file),
        "build_profile": build_profile,
        "build_features": build_features,
        "server_device_ids": server_device_ids,
        "client_device_ids": client_device_ids,
        "pd_url": pd_url,
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
        "prefix_cache": prefix_cache,
        "server_ready_timeout_seconds": server_ready_timeout_seconds,
        "pd_ready_timeout_seconds": pd_ready_timeout_seconds,
        "benchmark_timeout_seconds": benchmark_timeout_seconds,
        "request_timeout_seconds": request_timeout_seconds,
        "myelon_rpc_depth": int(myelon_rpc_depth) if myelon_rpc_depth else None,
        "myelon_response_depth": (
            int(myelon_response_depth) if myelon_response_depth else None
        ),
        "myelon_busy_spin": myelon_busy_spin,
        "expected_case_count": 0,
        "expected_case_labels": [],
        "cases": [],
    }

    if not model_capability["pd_supported"]:
        report["status"] = "skipped_unsupported_architecture"
        report["report_bundle"] = write_report_bundle(
            output_root=output_root,
            report=report,
            report_path=report_path,
            repo_root=repo_root,
            capture_raw_system=capture_raw_system,
        )
        report = normalize_report(report)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(report_path)
        return 0

    if not topology_capability["pd_supported"]:
        report["status"] = "skipped_unsupported_topology"
        report["report_bundle"] = write_report_bundle(
            output_root=output_root,
            report=report,
            report_path=report_path,
            repo_root=repo_root,
            capture_raw_system=capture_raw_system,
        )
        report = normalize_report(report)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(report_path)
        return 0

    if not transport_capability["pd_supported"]:
        report["status"] = "skipped_unsupported_transport"
        report["report_bundle"] = write_report_bundle(
            output_root=output_root,
            report=report,
            report_path=report_path,
            repo_root=repo_root,
            capture_raw_system=capture_raw_system,
        )
        report = normalize_report(report)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(report_path)
        return 0

    report["status"] = "completed"

    try:
        validate_device_roles(server_device_ids, client_device_ids)
    except ValueError as error:
        print(f"invalid PD device configuration: {error}", file=sys.stderr)
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

    base_env = os.environ.copy()
    compute_cap_override = os.environ.get("CUDA_COMPUTE_CAP")
    if compute_cap_override:
        base_env.setdefault("CUDA_COMPUTE_CAP", compute_cap_override)
    base_env.setdefault("KEEP_ALIVE_INTERVAL", env_str("VLLM_SERVER_KEEP_ALIVE_INTERVAL", "0"))

    try:
        cases = prepare_cases()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    report["expected_case_count"] = len(cases)
    report["expected_case_labels"] = [label for label, _, _ in cases]

    for label, server_extra_args, client_extra_args in cases:
        case_dir = output_root / label
        case_dir.mkdir(parents=True, exist_ok=True)

        pd_server_log_path = case_dir / "pd_server.log"
        client_server_log_path = case_dir / "client_server.log"
        benchmark_log_path = case_dir / "benchmark.log"
        benchmark_output_path = case_dir / "conversations.json"
        base_url = f"http://127.0.0.1:{client_port}"

        pd_server_command = [
            str(binary_path),
            "--pd-server",
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
            "--num-shards",
            "1",
            "--device-ids",
            server_device_ids_raw,
            *server_extra_args,
        ]
        if prefix_cache:
            pd_server_command.append("--prefix-cache")
        if pd_url:
            pd_server_command.extend(["--pd-url", pd_url])
        if label == "myelon_pd":
            if myelon_rpc_depth:
                pd_server_command.extend(["--myelon-rpc-depth", myelon_rpc_depth])
            if myelon_response_depth:
                pd_server_command.extend(
                    ["--myelon-response-depth", myelon_response_depth]
                )
            if myelon_busy_spin:
                pd_server_command.append("--myelon-busy-spin")

        client_server_command = [
            str(binary_path),
            "--server",
            "--port",
            str(client_port),
            "--pd-client",
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
            "--num-shards",
            "1",
            "--device-ids",
            client_device_ids_raw,
            *client_extra_args,
        ]
        if prefix_cache:
            client_server_command.append("--prefix-cache")
        if pd_url:
            client_server_command.extend(["--pd-url", pd_url])
        if label == "myelon_pd":
            if myelon_rpc_depth:
                client_server_command.extend(["--myelon-rpc-depth", myelon_rpc_depth])
            if myelon_response_depth:
                client_server_command.extend(
                    ["--myelon-response-depth", myelon_response_depth]
                )
            if myelon_busy_spin:
                client_server_command.append("--myelon-busy-spin")

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
            benchmark_command.extend(["--max-num-requests", str(max_num_requests)])
        if warmup_step:
            benchmark_command.append("--warmup-step")
        if no_stream:
            benchmark_command.append("--no-stream")

        case_report: dict[str, object] = {
            "label": label,
            "execution_variant": label,
            "stop_point": "full_completion",
            "skip_reason": None,
            "pd_server_command": pd_server_command,
            "client_server_command": client_server_command,
            "benchmark_command": benchmark_command,
            "pd_server_log_path": str(pd_server_log_path),
            "client_server_log_path": str(client_server_log_path),
            "benchmark_log_path": str(benchmark_log_path),
            "benchmark_output_path": str(benchmark_output_path),
        }

        with pd_server_log_path.open("wb") as pd_server_log:
            pd_server = subprocess.Popen(
                pd_server_command,
                cwd=repo_root,
                stdout=pd_server_log,
                stderr=subprocess.STDOUT,
                env=base_env,
            )

        client_server: subprocess.Popen[bytes] | None = None
        try:
            wait_for_pd_server_ready(pd_server_log_path, pd_server, pd_ready_timeout_seconds)

            with client_server_log_path.open("wb") as client_server_log:
                client_server = subprocess.Popen(
                    client_server_command,
                    cwd=repo_root,
                    stdout=client_server_log,
                    stderr=subprocess.STDOUT,
                    env=base_env,
                )

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
            if client_server is not None:
                case_report["client_server_exit_code"] = terminate_process(client_server, 10)
            case_report["pd_server_exit_code"] = terminate_process(pd_server, 10)

        report["cases"].append(case_report)
        if (
            case_report.get("skip_reason")
            or case_report.get("stop_point") != "full_completion"
            or case_report.get("benchmark_exit_code") not in (None, 0)
        ):
            report["status"] = "partial"
        report["report_bundle"] = write_report_bundle(
            output_root=output_root,
            report=report,
            report_path=report_path,
            repo_root=repo_root,
            capture_raw_system=capture_raw_system,
        )
        report = normalize_report(report)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
