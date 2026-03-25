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


def default_build_features() -> str:
    if platform.system() == "Darwin":
        return "metal,myelon"
    return "cuda,myelon"


def build_command(
    repo_root: Path,
    model_path: str,
    prompt: str,
    max_model_len: str,
    max_tokens: str,
    seed: str,
    num_shards: str,
    device_ids: str | None,
    myelon_rpc_depth: str | None,
    myelon_response_depth: str | None,
    myelon_busy_spin: bool,
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
        "--num-shards",
        num_shards,
        "--myelon-ipc",
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


def run_once(repo_root: Path, iteration: int, command: list[str], timeout_seconds: int) -> dict:
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
        "iteration": iteration,
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
    device_ids = os.environ.get("VLLM_DEVICE_IDS")
    myelon_rpc_depth = os.environ.get("VLLM_MYELON_RPC_DEPTH")
    myelon_response_depth = os.environ.get("VLLM_MYELON_RESPONSE_DEPTH")
    myelon_busy_spin = env_str("VLLM_MYELON_BUSY_SPIN", "0").lower() in {
        "1",
        "true",
        "yes",
    }
    timeout_seconds = int(env_str("VLLM_TIMEOUT_SECONDS", "60"))
    iterations = int(env_str("VLLM_RECOVERY_ITERATIONS", "3"))
    build_features = env_str("VLLM_BUILD_FEATURES", "cuda,myelon")
    if "VLLM_BUILD_FEATURES" not in os.environ:
        build_features = default_build_features()
    output_path = Path(
        env_str(
            "VLLM_RECOVERY_REPORT_OUT",
            str(repo_root / "target" / "myelon_recovery_report.json"),
        )
    )

    if not Path(model_path).is_dir():
        print(f"model path does not exist: {model_path}", file=sys.stderr)
        print(
            "set VLLM_MODEL_PATH to a local snapshot directory before running this script",
            file=sys.stderr,
        )
        return 1

    subprocess.run(
        ["cargo", "build", "--bin", "vllm-rs", "--bin", "runner", "--features", build_features],
        cwd=repo_root,
        check=True,
    )

    command = build_command(
        repo_root,
        model_path,
        prompt,
        max_model_len,
        max_tokens,
        seed,
        num_shards,
        device_ids,
        myelon_rpc_depth,
        myelon_response_depth,
        myelon_busy_spin,
    )

    results = []
    for iteration in range(1, iterations + 1):
        results.append(run_once(repo_root, iteration, command, timeout_seconds))

    first_response = results[0]["metrics"]["response"] if results else None
    all_responses_match = all(
        result["metrics"]["response"] == first_response for result in results
    )
    all_myelon_enabled = all(
        result["metrics"]["myelon_enabled"] for result in results
    )
    all_process_mode = all(
        result["metrics"]["runner_mode"] == "process" for result in results
    )

    report = {
        "model_path": model_path,
        "prompt": prompt,
        "max_model_len": int(max_model_len),
        "max_tokens": int(max_tokens),
        "seed": int(seed),
        "num_shards": int(num_shards),
        "device_ids": device_ids,
        "myelon_rpc_depth": int(myelon_rpc_depth) if myelon_rpc_depth else None,
        "myelon_response_depth": int(myelon_response_depth)
        if myelon_response_depth
        else None,
        "myelon_busy_spin": myelon_busy_spin,
        "iterations": iterations,
        "build_features": build_features,
        "all_responses_match": all_responses_match,
        "all_myelon_enabled": all_myelon_enabled,
        "all_process_mode": all_process_mode,
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output_path)

    if any(result["exit_code"] != 0 for result in results):
        return 1
    if not all_responses_match:
        return 2
    if not all_myelon_enabled or not all_process_mode:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
