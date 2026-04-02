import os
import platform
import subprocess


def env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def default_build_features() -> str:
    if platform.system() == "Darwin":
        return "metal,myelon"
    return "cuda,myelon,nccl"


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
