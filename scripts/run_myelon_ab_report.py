#!/usr/bin/env python3
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path


RESPONSE_RE = re.compile(r"Response:\s*(.*)")
PROMPT_METRICS_RE = re.compile(
    r"Prompt tokens:\s+(\d+)\s+in\s+([0-9.]+)s\s+\(([0-9.]+)\s+tokens/s\)"
)
DECODE_METRICS_RE = re.compile(
    r"Decoded tokens:\s+(\d+)\s+in\s+([0-9.]+)s\s+\(([0-9.]+)\s+tokens/s\)"
)
TOPOLOGY_RE = re.compile(
    r"Runner topology mode=(\w+) reason=([^\s]+) num_shards=(\d+) device_ids=\[([^\]]*)\]"
)


def env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return float(value)


def default_build_features() -> str:
    if platform.system() == "Darwin":
        return "metal,myelon"
    return "cuda,myelon"


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

    if "cuda" not in build_features.split(","):
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


def build_command(
    repo_root: Path,
    model_path: str,
    prompt: str,
    max_model_len: str,
    max_tokens: str,
    seed: str,
    device_ids: str | None,
    myelon_rpc_depth: str | None,
    myelon_response_depth: str | None,
    myelon_busy_spin: bool,
    extra_args: list[str],
) -> list[str]:
    command = [
        str(repo_root / "target" / "debug" / "vllm-rs"),
        "--w",
        model_path,
        "--max-num-seqs",
        "1",
        "--max-model-len",
        max_model_len,
        "--max-tokens",
        max_tokens,
        "--prompts",
        prompt,
        "--dtype",
        "bf16",
        "--seed",
        seed,
        *extra_args,
    ]
    if device_ids:
        command.extend(["--device-ids", device_ids])
    if myelon_rpc_depth:
        command.extend(["--myelon-rpc-depth", myelon_rpc_depth])
    if myelon_response_depth:
        command.extend(["--myelon-response-depth", myelon_response_depth])
    if myelon_busy_spin:
        command.append("--myelon-busy-spin")
    return command


def parse_metrics(output: str) -> dict:
    response_match = RESPONSE_RE.search(output)
    prompt_match = PROMPT_METRICS_RE.search(output)
    decode_match = DECODE_METRICS_RE.search(output)
    topology_match = TOPOLOGY_RE.search(output)

    metrics = {
        "response": response_match.group(1).strip() if response_match else None,
        "prompt_tokens": None,
        "prompt_seconds": None,
        "prompt_tokens_per_second": None,
        "decoded_tokens": None,
        "decode_seconds": None,
        "decode_tokens_per_second": None,
        "myelon_enabled": "Enabled Myelon IPC hot path across" in output,
        "myelon_first_request_logged": "Dispatching first Myelon request" in output,
        "myelon_first_response_logged": "Received first Myelon response" in output,
        "socket_shutdown_logged": "Runner exit" in output,
        "myelon_shutdown_logged": "Runner received Myelon shutdown." in output,
        "runner_mode": None,
        "runner_reason": None,
        "num_shards": None,
        "device_ids": None,
    }

    if prompt_match:
        metrics["prompt_tokens"] = int(prompt_match.group(1))
        metrics["prompt_seconds"] = float(prompt_match.group(2))
        metrics["prompt_tokens_per_second"] = float(prompt_match.group(3))

    if decode_match:
        metrics["decoded_tokens"] = int(decode_match.group(1))
        metrics["decode_seconds"] = float(decode_match.group(2))
        metrics["decode_tokens_per_second"] = float(decode_match.group(3))

    if topology_match:
        raw_device_ids = topology_match.group(4).strip()
        metrics["runner_mode"] = topology_match.group(1)
        metrics["runner_reason"] = topology_match.group(2)
        metrics["num_shards"] = int(topology_match.group(3))
        metrics["device_ids"] = (
            [int(part.strip()) for part in raw_device_ids.split(",") if part.strip()]
            if raw_device_ids
            else []
        )

    return metrics


def run_case(repo_root: Path, label: str, command: list[str], timeout_seconds: int) -> dict:
    started_at = time.time()
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    finished_at = time.time()
    combined_output = completed.stdout + completed.stderr
    return {
        "label": label,
        "command": command,
        "exit_code": completed.returncode,
        "elapsed_seconds": round(finished_at - started_at, 3),
        "metrics": parse_metrics(combined_output),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


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
