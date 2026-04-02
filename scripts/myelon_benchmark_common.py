#!/usr/bin/env python3
import re
import statistics
import subprocess
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

NUMERIC_METRICS = (
    "elapsed_seconds",
    "prompt_tokens",
    "prompt_seconds",
    "prompt_tokens_per_second",
    "decoded_tokens",
    "decode_seconds",
    "decode_tokens_per_second",
)


def build_command(
    repo_root: Path,
    binary_path: Path,
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
        str(binary_path),
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
        "runner_prefill_error_logged": "Runner prefill error:" in output,
        "engine_loop_error_logged": "[Engine Loop] Step error:" in output,
        "error_logged": " ERROR " in output,
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


def run_case_with_retries(
    repo_root: Path,
    label: str,
    command: list[str],
    timeout_seconds: int,
    max_attempts: int,
    retry_sleep_seconds: float,
) -> dict:
    attempts = []
    for attempt_index in range(max_attempts):
        run = run_case(repo_root, label, command, timeout_seconds)
        attempts.append(run)
        if run["exit_code"] == 0 and metrics_are_complete(run["metrics"]):
            final_run = dict(run)
            final_run["attempt_count"] = attempt_index + 1
            final_run["retried"] = attempt_index > 0
            final_run["attempts"] = [dict(attempt) for attempt in attempts]
            return final_run
        if attempt_index + 1 < max_attempts and retry_sleep_seconds > 0:
            time.sleep(retry_sleep_seconds)

    final_run = dict(attempts[-1])
    final_run["attempt_count"] = len(attempts)
    final_run["retried"] = len(attempts) > 1
    final_run["attempts"] = [dict(attempt) for attempt in attempts]
    return final_run


def summarize_numeric_runs(runs: list[dict]) -> dict:
    summary: dict[str, dict[str, float | int]] = {}
    for key in NUMERIC_METRICS:
        values = [run["metrics"].get(key, run.get(key)) for run in runs]
        normalized = [value for value in values if isinstance(value, (int, float))]
        if not normalized:
            continue
        summary[key] = {
            "count": len(normalized),
            "mean": round(statistics.fmean(normalized), 6),
            "median": round(statistics.median(normalized), 6),
            "min": round(min(normalized), 6),
            "max": round(max(normalized), 6),
        }
        if len(normalized) >= 2:
            summary[key]["stdev"] = round(statistics.stdev(normalized), 6)
    return summary


def metrics_are_complete(metrics: dict) -> bool:
    if metrics.get("response") is None:
        return False
    if metrics.get("prompt_tokens") is None or metrics.get("decoded_tokens") is None:
        return False
    if metrics.get("prompt_seconds") is None or metrics.get("decode_seconds") is None:
        return False
    if metrics.get("prompt_tokens_per_second") is None or metrics.get(
        "decode_tokens_per_second"
    ) is None:
        return False
    if metrics.get("runner_prefill_error_logged") or metrics.get("engine_loop_error_logged"):
        return False
    return not metrics.get("error_logged", False)
