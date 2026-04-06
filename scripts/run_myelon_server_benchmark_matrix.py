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

from myelon_report_common import normalize_report, write_report_bundle
from myelon_validation_common import (
    build_benchmark_contract,
    build_machine_profile,
    classify_arrival_pattern,
    classify_model_capability,
    default_build_features,
    env_str,
    extract_server_kvcache_plan,
    infer_request_run_class,
    infer_workload_class_from_path,
    parse_device_ids,
    resolve_cache_pressure_profile,
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
    r"^.*\[(ttft_ms|tpot_ms|latency_ms)\s*\]\s+avg:\s+([0-9.]+),\s+min:\s+([0-9.]+),\s+max:\s+([0-9.]+)$",
    re.MULTILINE,
)

VALID_SERVER_SUBMODES = {
    "serving_qos": {"cold_turn", "cold_turn_idle_gap", "warm_steady_state"},
    "server_prefill_stress": {
        "fixed_prompt_burst",
        "low_decode",
        "cache_thrash_round_robin",
        "shared_prefix_round_robin_control",
    },
}

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


def env_optional_bool(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return value.lower() in {"1", "true", "yes"}


def env_optional_float(name: str) -> float | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return float(value)


def env_optional_int(name: str) -> int | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return int(value)


def env_optional_str(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return value


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


def resolve_server_benchmark_family(explicit: str | None) -> str:
    if explicit is None or explicit.strip() == "":
        return "serving_qos"
    candidate = explicit.strip()
    if candidate not in {"serving_qos", "server_prefill_stress"}:
        raise ValueError(
            "unsupported VLLM_SERVER_BENCHMARK_FAMILY "
            f"{candidate!r}; expected 'serving_qos' or 'server_prefill_stress'"
        )
    return candidate


def infer_server_benchmark_submode(
    benchmark_family: str,
    explicit: str | None,
) -> str:
    if explicit is not None and explicit.strip():
        candidate = explicit.strip()
    elif benchmark_family == "serving_qos":
        candidate = "warm_steady_state"
    else:
        candidate = "cache_thrash_round_robin"
    valid_submodes = VALID_SERVER_SUBMODES[benchmark_family]
    if candidate not in valid_submodes:
        raise ValueError(
            f"unsupported {benchmark_family} submode {candidate!r}; "
            f"expected one of {sorted(valid_submodes)}"
        )
    return candidate


def expected_warmup_step(
    benchmark_family: str,
    benchmark_submode: str,
) -> bool:
    if benchmark_family == "serving_qos":
        return benchmark_submode == "warm_steady_state"
    return False


def resolve_serving_qos_defaults(benchmark_submode: str) -> dict[str, object]:
    if benchmark_submode == "cold_turn_idle_gap":
        return {
            "warmup_step": False,
            "num_clients": 1,
            "max_active_conversations": 2,
            "max_num_requests": 16,
            "max_turns": 2,
            "request_rate": 1.0,
        }
    if benchmark_submode == "cold_turn":
        return {
            "warmup_step": False,
            "num_clients": 1,
            "max_active_conversations": 2,
            "max_num_requests": 16,
            "max_turns": 2,
            "request_rate": 0.0,
        }
    return {
        "warmup_step": True,
        "num_clients": 1,
        "max_active_conversations": 2,
        "max_num_requests": 16,
        "max_turns": 2,
        "request_rate": 0.0,
    }


def default_server_workload_path(
    repo_root: Path,
    benchmark_family: str,
    benchmark_submode: str,
) -> Path:
    if benchmark_family == "server_prefill_stress":
        inputs_dir = repo_root / "artifacts" / "h100_benchmarking_2026_04_06" / "inputs"
        if benchmark_submode == "fixed_prompt_burst":
            return inputs_dir / "synthetic_server_prefill_fixed_prompt_burst.json"
        if benchmark_submode == "shared_prefix_round_robin_control":
            return inputs_dir / "synthetic_server_prefill_shared_prefix_round_robin.json"
        return inputs_dir / "synthetic_server_prefill_stress_round_robin.json"
    return (
        repo_root
        / "artifacts"
        / "b300_benchmarking_2026_04_02"
        / "synthetic_multi_turn_smoke.json"
    )


def env_or_default_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def env_or_default_float_string(name: str, default: float) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return str(default)
    return value


def resolve_server_prefill_defaults(benchmark_submode: str) -> dict[str, object]:
    if benchmark_submode == "fixed_prompt_burst":
        return {
            "warmup_step": False,
            "num_clients": 1,
            "max_active_conversations": 32,
            "max_num_seqs": 32,
            "max_num_requests": 32,
            "max_turns": 2,
            "request_rate": "0",
            "conversation_sampling": "round_robin",
            "limit_min_tokens": 1,
            "limit_max_tokens": 1,
            "prefix_cache_enabled": False,
            "kv_fraction": 0.55,
            "cpu_mem_fold": 0.5,
        }
    if benchmark_submode == "low_decode":
        return {
            "warmup_step": False,
            "num_clients": 16,
            "max_active_conversations": 32,
            "max_num_seqs": 32,
            "max_num_requests": 192,
            "max_turns": 6,
            "request_rate": "0",
            "conversation_sampling": "round_robin",
            "limit_min_tokens": 16,
            "limit_max_tokens": 32,
            "prefix_cache_enabled": False,
            "kv_fraction": 0.55,
            "cpu_mem_fold": 0.5,
        }
    if benchmark_submode == "shared_prefix_round_robin_control":
        return {
            "warmup_step": False,
            "num_clients": 32,
            "max_active_conversations": 64,
            "max_num_seqs": 64,
            "max_num_requests": 384,
            "max_turns": 6,
            "request_rate": "0",
            "conversation_sampling": "round_robin",
            "limit_min_tokens": 8,
            "limit_max_tokens": 8,
            "prefix_cache_enabled": True,
            "prefix_cache_max_tokens": 32768,
            "kv_fraction": 0.55,
            "cpu_mem_fold": 0.5,
        }
    return {
        "warmup_step": False,
        "num_clients": 32,
        "max_active_conversations": 64,
        "max_num_seqs": 64,
        "max_num_requests": 384,
        "max_turns": 6,
        "request_rate": "0",
        "conversation_sampling": "round_robin",
        "limit_min_tokens": 8,
        "limit_max_tokens": 8,
        "prefix_cache_enabled": True,
        "prefix_cache_max_tokens": 1024,
        "kv_fraction": 0.08,
        "cpu_mem_fold": 0.05,
    }


def apply_server_prefill_cache_pressure_defaults(
    benchmark_submode: str,
    cache_pressure_profile: str | None,
    defaults: dict[str, object],
) -> dict[str, object]:
    resolved = dict(defaults)
    if cache_pressure_profile != "swap_pressure":
        return resolved
    if benchmark_submode == "fixed_prompt_burst":
        return resolved
    resolved["prefix_cache_enabled"] = True
    resolved["prefix_cache_max_tokens"] = 512
    resolved["kv_fraction"] = 0.08
    resolved["cpu_mem_fold"] = 2.0
    resolved["limit_min_tokens"] = 32
    resolved["limit_max_tokens"] = 32
    return resolved


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


def should_abort_swap_pressure_for_seq_capacity(
    cache_pressure_profile: str,
    allocator_plan: dict[str, int] | None,
) -> bool:
    if cache_pressure_profile != "swap_pressure" or allocator_plan is None:
        return False
    planned_max_seqs = allocator_plan.get("planned_max_seqs")
    if planned_max_seqs is None:
        return False
    return planned_max_seqs < 4


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    upstream_repo_root = repo_root.parent / "vllm"
    upstream_benchmark_script = (
        upstream_repo_root / "benchmarks" / "multi_turn" / "benchmark_serving_multi_turn.py"
    )
    fixed_prompt_burst_script = (
        repo_root / "scripts" / "benchmark_server_fixed_prompt_burst.py"
    )
    benchmark_family = resolve_server_benchmark_family(
        os.environ.get("VLLM_SERVER_BENCHMARK_FAMILY")
    )
    try:
        benchmark_submode = infer_server_benchmark_submode(
            benchmark_family,
            os.environ.get("VLLM_SERVER_BENCHMARK_SUBMODE"),
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    requested_cache_pressure_profile = env_optional_str("VLLM_CACHE_PRESSURE_PROFILE")
    prefill_defaults = {}
    serving_defaults = {}
    if benchmark_family == "server_prefill_stress":
        prefill_defaults = apply_server_prefill_cache_pressure_defaults(
            benchmark_submode,
            requested_cache_pressure_profile.strip()
            if requested_cache_pressure_profile is not None
            else None,
            resolve_server_prefill_defaults(benchmark_submode),
        )
    else:
        serving_defaults = resolve_serving_qos_defaults(benchmark_submode)
    workload_default = default_server_workload_path(
        repo_root,
        benchmark_family,
        benchmark_submode,
    )
    model_path = env_str(
        "VLLM_MODEL_PATH",
        "/root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c",
    )
    workload_file = Path(
        env_str(
            "VLLM_BENCHMARK_INPUT_FILE",
            str(workload_default),
        )
    )
    mode = env_str("VLLM_SERVER_BENCHMARK_MODE", "single_gpu")
    seed = env_str("VLLM_SEED", "123")
    build_profile = env_str("VLLM_BUILD_PROFILE", "release")
    build_features = env_str("VLLM_BUILD_FEATURES", "")
    device_ids = os.environ.get("VLLM_DEVICE_IDS")
    parsed_device_ids = parse_device_ids(device_ids)
    server_ready_timeout_seconds = env_int("VLLM_SERVER_READY_TIMEOUT_SECONDS", 300)
    benchmark_timeout_seconds = env_int("VLLM_SERVER_BENCH_TIMEOUT_SECONDS", 900)
    request_timeout_seconds = env_int("VLLM_SERVER_REQUEST_TIMEOUT_SECONDS", 180)
    myelon_rpc_depth = env_str("VLLM_MYELON_RPC_DEPTH", "8192")
    myelon_response_depth = env_str("VLLM_MYELON_RESPONSE_DEPTH", "8192")
    myelon_busy_spin = env_str("VLLM_MYELON_BUSY_SPIN", "1").lower() in {
        "1",
        "true",
        "yes",
    }
    num_clients = env_or_default_int(
        "VLLM_SERVER_BENCH_NUM_CLIENTS",
        int(prefill_defaults.get("num_clients", serving_defaults.get("num_clients", 2))),
    )
    max_active_conversations = env_or_default_int(
        "VLLM_SERVER_BENCH_MAX_ACTIVE_CONVERSATIONS",
        int(
            prefill_defaults.get(
                "max_active_conversations",
                serving_defaults.get("max_active_conversations", 4),
            )
        ),
    )
    max_num_requests = env_or_default_int(
        "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS",
        int(
            prefill_defaults.get(
                "max_num_requests",
                serving_defaults.get("max_num_requests", 16),
            )
        ),
    )
    max_turns = env_or_default_int(
        "VLLM_SERVER_BENCH_MAX_TURNS",
        int(prefill_defaults.get("max_turns", serving_defaults.get("max_turns", 4))),
    )
    explicit_max_num_seqs = env_optional_int("VLLM_SERVER_MAX_NUM_SEQS")
    if explicit_max_num_seqs is not None:
        max_num_seqs = explicit_max_num_seqs
    elif benchmark_family == "server_prefill_stress":
        max_num_seqs = max(
            max_active_conversations,
            int(prefill_defaults.get("max_num_seqs", max_active_conversations)),
        )
    else:
        max_num_seqs = 8
    max_retries = env_int("VLLM_SERVER_BENCH_MAX_RETRIES", 1)
    request_rate = env_or_default_float_string(
        "VLLM_SERVER_BENCH_REQUEST_RATE",
        float(prefill_defaults.get("request_rate", serving_defaults.get("request_rate", 0.0))),
    )
    port_base = env_int("VLLM_SERVER_BENCH_PORT_BASE", 18080)
    explicit_warmup_step = env_optional_bool("VLLM_SERVER_BENCH_WARMUP_STEP")
    default_warmup_step = (
        expected_warmup_step(benchmark_family, benchmark_submode)
        if benchmark_family == "serving_qos"
        else bool(prefill_defaults.get("warmup_step", False))
    )
    if explicit_warmup_step is not None:
        expected = expected_warmup_step(benchmark_family, benchmark_submode)
        if explicit_warmup_step != expected:
            print(
                "VLLM_SERVER_BENCH_WARMUP_STEP conflicts with "
                f"{benchmark_family}.{benchmark_submode}",
                file=sys.stderr,
            )
            return 1
    warmup_step = explicit_warmup_step if explicit_warmup_step is not None else default_warmup_step
    no_stream = env_bool("VLLM_SERVER_BENCH_NO_STREAM", False)
    conversation_sampling = env_str(
        "VLLM_SERVER_BENCH_CONVERSATION_SAMPLING",
        str(prefill_defaults.get("conversation_sampling", "round_robin")),
    )
    limit_min_tokens = env_or_default_int(
        "VLLM_SERVER_BENCH_LIMIT_MIN_TOKENS",
        int(prefill_defaults.get("limit_min_tokens", -1)),
    )
    limit_max_tokens = env_or_default_int(
        "VLLM_SERVER_BENCH_LIMIT_MAX_TOKENS",
        int(prefill_defaults.get("limit_max_tokens", -1)),
    )
    explicit_prefix_cache_enabled = env_optional_bool("VLLM_SERVER_PREFIX_CACHE")
    prefix_cache_enabled = (
        explicit_prefix_cache_enabled
        if explicit_prefix_cache_enabled is not None
        else bool(prefill_defaults.get("prefix_cache_enabled", False))
    )
    prefix_cache_max_tokens = env_optional_int("VLLM_SERVER_PREFIX_CACHE_MAX_TOKENS")
    if prefix_cache_max_tokens is None and "prefix_cache_max_tokens" in prefill_defaults:
        prefix_cache_max_tokens = int(prefill_defaults["prefix_cache_max_tokens"])
    kv_fraction = env_optional_float("VLLM_SERVER_KV_FRACTION")
    if kv_fraction is None and "kv_fraction" in prefill_defaults:
        kv_fraction = float(prefill_defaults["kv_fraction"])
    cpu_mem_fold = env_optional_float("VLLM_SERVER_CPU_MEM_FOLD")
    if cpu_mem_fold is None and "cpu_mem_fold" in prefill_defaults:
        cpu_mem_fold = float(prefill_defaults["cpu_mem_fold"])
    explicit_max_model_len = env_optional_str("VLLM_MAX_MODEL_LEN")
    explicit_kv_fraction = env_optional_str("VLLM_SERVER_KV_FRACTION")
    if explicit_max_model_len is not None and explicit_kv_fraction is not None:
        print(
            "VLLM_MAX_MODEL_LEN and VLLM_SERVER_KV_FRACTION cannot both be set explicitly",
            file=sys.stderr,
        )
        return 1
    if explicit_max_model_len is not None:
        max_model_len: str | None = explicit_max_model_len
        if benchmark_family == "server_prefill_stress" and explicit_kv_fraction is None:
            kv_fraction = None
    elif benchmark_family == "server_prefill_stress" and kv_fraction is not None:
        max_model_len = None
    else:
        max_model_len = "1024"
    cache_pressure_profile = resolve_cache_pressure_profile(
        os.environ.get("VLLM_CACHE_PRESSURE_PROFILE"),
        kv_fraction=kv_fraction,
        prefix_cache_enabled=prefix_cache_enabled,
        prefix_cache_max_tokens=prefix_cache_max_tokens,
        cpu_mem_fold=cpu_mem_fold,
    )
    capture_raw_system = env_bool("VLLM_CAPTURE_RAW_SYSTEM_INFO", True)
    fixed_prompt_text = env_str(
        "VLLM_SERVER_FIXED_PROMPT_TEXT",
        "Please talk about China in more details.",
    )
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
    if not fixed_prompt_burst_script.is_file():
        print(f"fixed prompt burst benchmark script does not exist: {fixed_prompt_burst_script}", file=sys.stderr)
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
        "status": "completed",
        "mode": mode,
        "model_path": model_path,
        "workload_file": str(workload_file),
        "build_profile": build_profile,
        "build_features": build_features,
        "device_ids": device_ids,
        "parsed_device_ids": parsed_device_ids,
        "detected_cuda_device_count": detected_cuda_device_count,
        "max_model_len": int(max_model_len) if max_model_len is not None else None,
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
        "conversation_sampling": conversation_sampling,
        "limit_min_tokens": limit_min_tokens,
        "limit_max_tokens": limit_max_tokens,
        "server_ready_timeout_seconds": server_ready_timeout_seconds,
        "benchmark_timeout_seconds": benchmark_timeout_seconds,
        "request_timeout_seconds": request_timeout_seconds,
        "myelon_rpc_depth": int(myelon_rpc_depth) if myelon_rpc_depth else None,
        "myelon_response_depth": (
            int(myelon_response_depth) if myelon_response_depth else None
        ),
        "myelon_busy_spin": myelon_busy_spin,
        "benchmark_family": benchmark_family,
        "benchmark_submode": benchmark_submode,
        "prefix_cache_enabled": prefix_cache_enabled,
        "prefix_cache_max_tokens": prefix_cache_max_tokens,
        "kv_fraction": kv_fraction,
        "cpu_mem_fold": cpu_mem_fold,
        "cache_pressure_profile": cache_pressure_profile,
        "expected_case_count": 0,
        "expected_case_labels": [],
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
    report["expected_case_count"] = len(cases)
    report["expected_case_labels"] = [label for label, _ in cases]

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
        benchmark_family=benchmark_family,
        benchmark_submode=benchmark_submode,
        question_answered=(
            "What user-facing QoS difference does Myelon produce in persistent serving?"
            if benchmark_family == "serving_qos"
            else "How much shared-memory gain survives when the full server path stays in the loop under cache-hostile, prefill-dominant conditions?"
        ),
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
            "conversation_sampling": conversation_sampling,
            "limit_min_tokens": limit_min_tokens if limit_min_tokens > 0 else None,
            "limit_max_tokens": limit_max_tokens if limit_max_tokens > 0 else None,
            "mode": mode,
        },
        cache_pressure_profile=cache_pressure_profile,
        equivalence_group=(
            "fixed_prompt_burst_bridge"
            if benchmark_family == "server_prefill_stress"
            and benchmark_submode == "fixed_prompt_burst"
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
        stop_point="full_completion",
        skip_reason=None,
    )
    machine_profile = build_machine_profile(
        detected_cuda_device_count=detected_cuda_device_count,
        effective_device_ids=effective_device_ids,
    )
    model_capability = classify_model_capability(model_path)
    report["effective_device_ids"] = effective_device_ids
    report["benchmark_contract"] = benchmark_contract
    report["machine_profile"] = machine_profile
    report["model_capability"] = model_capability

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
            "--max-num-seqs",
            str(max_num_seqs),
            "--dtype",
            "bf16",
            "--seed",
            seed,
            *topology_args,
        ]
        if max_model_len is not None:
            server_command.extend(["--max-model-len", max_model_len])
        if effective_device_ids_str:
            server_command.extend(["--device-ids", effective_device_ids_str])
        if label == "myelon":
            if myelon_rpc_depth:
                server_command.extend(["--myelon-rpc-depth", myelon_rpc_depth])
            if myelon_response_depth:
                server_command.extend(
                    ["--myelon-response-depth", myelon_response_depth]
                )
            if myelon_busy_spin:
                server_command.append("--myelon-busy-spin")
        if prefix_cache_enabled:
            server_command.append("--prefix-cache")
        if prefix_cache_max_tokens is not None:
            server_command.extend(
                ["--prefix-cache-max-tokens", str(prefix_cache_max_tokens)]
            )
        if kv_fraction is not None:
            server_command.extend(["--kv-fraction", str(kv_fraction)])
        if cpu_mem_fold is not None:
            server_command.extend(["--cpu-mem-fold", str(cpu_mem_fold)])

        if benchmark_family == "server_prefill_stress" and benchmark_submode == "fixed_prompt_burst":
            benchmark_command = [
                "uv",
                "run",
                "--with",
                "aiohttp",
                "python3",
                str(fixed_prompt_burst_script),
                "--url",
                base_url,
                "--output-file",
                str(benchmark_output_path),
                "--prompt-text",
                fixed_prompt_text,
                "--num-requests",
                str(max_num_requests if max_num_requests > 0 else max_active_conversations),
                "--concurrency",
                str(max_active_conversations),
                "--max-tokens",
                str(limit_max_tokens if limit_max_tokens > 0 else 1),
                "--request-timeout-sec",
                str(request_timeout_seconds),
            ]
            if no_stream:
                benchmark_command.append("--no-stream")
        else:
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
                "--conversation-sampling",
                conversation_sampling,
            ]
            if max_num_requests > 0:
                benchmark_command.extend(
                    [
                        "--max-num-requests",
                        str(max_num_requests),
                    ]
                )
            if limit_min_tokens > 0:
                benchmark_command.extend(["--limit-min-tokens", str(limit_min_tokens)])
            if limit_max_tokens > 0:
                benchmark_command.extend(["--limit-max-tokens", str(limit_max_tokens)])
            if warmup_step:
                benchmark_command.append("--warmup-step")
            if no_stream:
                benchmark_command.append("--no-stream")

        case_report: dict[str, object] = {
            "label": label,
            "execution_variant": label,
            "stop_point": "full_completion",
            "skip_reason": None,
            "cache_pressure_profile": cache_pressure_profile,
            "conversation_sampling": conversation_sampling,
            "limit_min_tokens": limit_min_tokens if limit_min_tokens > 0 else None,
            "limit_max_tokens": limit_max_tokens if limit_max_tokens > 0 else None,
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
            allocator_plan = extract_server_kvcache_plan(server_log_path)
            if allocator_plan is not None:
                case_report["allocator_plan"] = allocator_plan

            benchmark_command_with_model = list(benchmark_command)
            benchmark_command_with_model.extend(["--served-model-name", served_model_name])
            case_report["benchmark_command"] = benchmark_command_with_model

            if should_abort_swap_pressure_for_seq_capacity(
                cache_pressure_profile,
                allocator_plan,
            ):
                case_report["benchmark_exit_code"] = None
                case_report["stop_point"] = "allocator_seq_capacity_collapse"
                case_report["skip_reason"] = (
                    "swap_pressure_profile_collapsed_effective_seq_capacity"
                )
                benchmark_log_path.write_text(
                    "benchmark skipped: allocator plan collapsed effective server "
                    f"capacity to {allocator_plan['planned_max_seqs']} seq(s) x "
                    f"{allocator_plan['planned_tokens_per_seq_limit']} tokens under "
                    "swap_pressure profile\n",
                    encoding="utf-8",
                )
            else:
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
                case_report["benchmark_elapsed_seconds"] = round(
                    finished_at - started_at, 3
                )
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
