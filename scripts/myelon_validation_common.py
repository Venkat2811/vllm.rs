import os
import platform
import socket
import subprocess
import json
from pathlib import Path


def env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def default_build_features() -> str:
    if platform.system() == "Darwin":
        return "metal,myelon"
    return "cuda,myelon,nccl"


VALID_RUN_CLASSES = frozenset({"smoke", "quickpass", "fullpass"})
VALID_BENCHMARK_FAMILIES = frozenset({"prefill_stress", "serving_qos", "pd_qos"})


def resolve_run_class(explicit: str | None, inferred_default: str) -> str:
    candidate = explicit.strip() if explicit else inferred_default.strip()
    if candidate not in VALID_RUN_CLASSES:
        raise ValueError(
            f"invalid run class {candidate!r}; expected one of {sorted(VALID_RUN_CLASSES)}"
        )
    return candidate


def infer_cli_run_class(measured_runs: int) -> str:
    if measured_runs <= 0:
        raise ValueError("measured runs must be > 0")
    return "fullpass" if measured_runs >= 5 else "quickpass"


def infer_request_run_class(max_num_requests: int | None) -> str:
    if max_num_requests is None:
        return "fullpass"
    if max_num_requests <= 0:
        raise ValueError("max_num_requests must be positive when provided")
    return "fullpass" if max_num_requests >= 32 else "quickpass"


def classify_arrival_pattern(request_rate: str | float | int | None) -> str:
    if request_rate is None:
        return "unspecified"
    if isinstance(request_rate, str):
        stripped = request_rate.strip()
        if stripped == "":
            return "unspecified"
        value = float(stripped)
    else:
        value = float(request_rate)
    if value <= 0:
        return "saturation_zero_gap"
    return "configured_fixed_rate"


def infer_workload_class_from_path(path: str) -> str:
    lowered = path.lower()
    if "sharegpt" in lowered:
        return "sharegpt_bounded"
    if "synthetic" in lowered:
        return "synthetic_multi_turn"
    if "first_transfer" in lowered or "transfer_first" in lowered:
        return "pd_first_transfer_control"
    return "file_defined"


def load_model_config(model_path: str | Path) -> dict[str, object] | None:
    config_path = Path(model_path) / "config.json"
    if not config_path.is_file():
        return None
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def classify_model_capability(model_path: str | Path) -> dict[str, object]:
    config = load_model_config(model_path)
    architectures = config.get("architectures", []) if isinstance(config, dict) else []
    architecture = architectures[0] if architectures else None
    model_type = config.get("model_type") if isinstance(config, dict) else None

    layer_types = []
    if isinstance(config, dict):
        text_config = config.get("text_config")
        if isinstance(text_config, dict):
            raw_layer_types = text_config.get("layer_types")
            if isinstance(raw_layer_types, list):
                layer_types = [str(item) for item in raw_layer_types]
        raw_layer_types = config.get("layer_types")
        if isinstance(raw_layer_types, list) and not layer_types:
            layer_types = [str(item) for item in raw_layer_types]

    searchable = []
    if architecture:
        searchable.append(str(architecture).lower())
    if model_type:
        searchable.append(str(model_type).lower())
    searchable.extend(item.lower() for item in layer_types)

    has_linear_attention = any("linear_attention" in item for item in searchable)
    has_mamba = any("mamba" in item for item in searchable)
    pd_supported = not (has_linear_attention or has_mamba)
    pd_skip_reason = (
        None if pd_supported else "unsupported_architecture_pd_state_transfer"
    )

    return {
        "architecture": architecture,
        "architectures": architectures,
        "model_type": model_type,
        "layer_types": layer_types,
        "pd_supported": pd_supported,
        "pd_skip_reason": pd_skip_reason,
    }


def classify_pd_topology_capability(
    server_device_ids: list[int] | None,
    client_device_ids: list[int] | None,
    detected_cuda_device_count: int | None,
) -> dict[str, object]:
    skip_reason = None
    if server_device_ids is None or client_device_ids is None:
        skip_reason = "unsupported_topology_pd_requires_explicit_single_device_roles"
    elif len(server_device_ids) != 1 or len(client_device_ids) != 1:
        skip_reason = "unsupported_topology_pd_requires_single_device_server_and_client"
    elif server_device_ids[0] == client_device_ids[0]:
        skip_reason = "unsupported_topology_pd_requires_distinct_server_client_devices"
    elif detected_cuda_device_count is not None:
        invalid_server = [
            device_id for device_id in server_device_ids if device_id >= detected_cuda_device_count
        ]
        invalid_client = [
            device_id for device_id in client_device_ids if device_id >= detected_cuda_device_count
        ]
        if invalid_server or invalid_client:
            skip_reason = "unsupported_topology_insufficient_visible_cuda_devices"

    return {
        "server_device_ids": server_device_ids,
        "client_device_ids": client_device_ids,
        "detected_cuda_device_count": detected_cuda_device_count,
        "pd_supported": skip_reason is None,
        "pd_skip_reason": skip_reason,
    }


def detect_gpu_inventory() -> list[dict[str, object]] | None:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,uuid,pci.bus_id,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None

    inventory: list[dict[str, object]] = []
    for raw_line in completed.stdout.splitlines():
        parts = [part.strip() for part in raw_line.split(",")]
        if len(parts) != 6:
            continue
        memory_total_mib = None
        try:
            memory_total_mib = int(parts[4])
        except ValueError:
            memory_total_mib = None
        inventory.append(
            {
                "index": int(parts[0]),
                "name": parts[1],
                "uuid": parts[2],
                "pci_bus_id": parts[3],
                "memory_total_mib": memory_total_mib,
                "driver_version": parts[5],
            }
        )
    return inventory


def build_machine_profile(
    detected_cuda_device_count: int | None,
    effective_device_ids: list[int] | None = None,
) -> dict[str, object]:
    return {
        "hostname": socket.gethostname(),
        "system": platform.system(),
        "release": platform.release(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "cuda_compute_cap_override": os.environ.get("CUDA_COMPUTE_CAP"),
        "detected_cuda_device_count": detected_cuda_device_count,
        "effective_device_ids": effective_device_ids,
        "gpu_inventory": detect_gpu_inventory(),
    }


def build_benchmark_contract(
    benchmark_family: str,
    benchmark_submode: str,
    question_answered: str,
    workload_class: str,
    warmup_policy: str,
    first_turn_measured: bool | None,
    arrival_pattern: str,
    concurrency_policy: dict[str, object],
    topology_overlay: str,
    transport_mode: str,
    run_class: str,
    stop_point: str,
    skip_reason: str | None,
) -> dict[str, object]:
    if benchmark_family not in VALID_BENCHMARK_FAMILIES:
        raise ValueError(
            f"invalid benchmark family {benchmark_family!r}; "
            f"expected one of {sorted(VALID_BENCHMARK_FAMILIES)}"
        )
    if not question_answered.strip():
        raise ValueError("question_answered must be non-empty")
    if not benchmark_submode.strip():
        raise ValueError("benchmark_submode must be non-empty")
    if not workload_class.strip():
        raise ValueError("workload_class must be non-empty")
    if not warmup_policy.strip():
        raise ValueError("warmup_policy must be non-empty")
    if not arrival_pattern.strip():
        raise ValueError("arrival_pattern must be non-empty")
    if not isinstance(concurrency_policy, dict) or not concurrency_policy:
        raise ValueError("concurrency_policy must be a non-empty dict")
    if not topology_overlay.strip():
        raise ValueError("topology_overlay must be non-empty")
    if not transport_mode.strip():
        raise ValueError("transport_mode must be non-empty")
    if run_class not in VALID_RUN_CLASSES:
        raise ValueError(
            f"invalid run class {run_class!r}; expected one of {sorted(VALID_RUN_CLASSES)}"
        )
    if not stop_point.strip():
        raise ValueError("stop_point must be non-empty")
    if skip_reason is not None and not skip_reason.strip():
        raise ValueError("skip_reason must be non-empty when provided")

    return {
        "benchmark_family": benchmark_family,
        "benchmark_submode": benchmark_submode,
        "question_answered": question_answered,
        "workload_class": workload_class,
        "warmup_policy": warmup_policy,
        "first_turn_measured": first_turn_measured,
        "arrival_pattern": arrival_pattern,
        "concurrency_policy": concurrency_policy,
        "topology_overlay": topology_overlay,
        "transport_mode": transport_mode,
        "run_class": run_class,
        "stop_point": stop_point,
        "skip_reason": skip_reason,
    }


def parse_device_ids(device_ids: str | None) -> list[int] | None:
    if device_ids is None or device_ids.strip() == "":
        return None

    parsed = []
    for raw in device_ids.split(","):
        stripped = raw.strip()
        if stripped == "":
            raise ValueError(f"invalid VLLM_DEVICE_IDS value '{device_ids}': empty entry")
        parsed.append(int(stripped))
    return parsed


def detect_cuda_device_count() -> int | None:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible is not None and visible.strip() != "":
        tokens = [part.strip() for part in visible.split(",") if part.strip()]
        return len(tokens)

    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return len(lines)


def validate_requested_topology(
    parsed_num_shards: int,
    parsed_device_ids: list[int] | None,
    build_features: str,
) -> int | None:
    if parsed_num_shards <= 0:
        raise ValueError("VLLM_NUM_SHARDS must be greater than zero")

    if parsed_device_ids is not None and len(parsed_device_ids) != parsed_num_shards:
        raise ValueError(
            "VLLM_NUM_SHARDS must match the number of ids in VLLM_DEVICE_IDS: "
            f"num_shards={parsed_num_shards}, device_ids={parsed_device_ids}"
        )

    enabled_features = {feature.strip() for feature in build_features.split(",") if feature.strip()}

    if parsed_num_shards > 1 and "nccl" not in enabled_features:
        raise ValueError(
            "multi-GPU tensor parallel requires the `nccl` cargo feature; "
            f"requested num_shards={parsed_num_shards} with build_features={build_features!r}"
        )

    if "cuda" not in enabled_features:
        return None

    detected_count = detect_cuda_device_count()
    if detected_count is None:
        return None

    if parsed_device_ids is None:
        if parsed_num_shards > detected_count:
            raise ValueError(
                f"requested num_shards={parsed_num_shards} but only {detected_count} CUDA "
                "device(s) are visible on this host"
            )
        return detected_count

    invalid_ids = [device_id for device_id in parsed_device_ids if device_id >= detected_count]
    if invalid_ids:
        raise ValueError(
            f"requested device_ids={parsed_device_ids} but only {detected_count} CUDA "
            f"device(s) are visible on this host"
        )
    return detected_count
