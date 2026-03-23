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


def env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def default_build_features() -> str:
    if platform.system() == "Darwin":
        return "metal,myelon"
    return "cuda,myelon"


def build_command(repo_root: Path, model_path: str, prompt: str, max_model_len: str, max_tokens: str, seed: str, extra_args: list[str]) -> list[str]:
    return [
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


def parse_metrics(output: str) -> dict:
    response_match = RESPONSE_RE.search(output)
    prompt_match = PROMPT_METRICS_RE.search(output)
    decode_match = DECODE_METRICS_RE.search(output)

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
    }

    if prompt_match:
        metrics["prompt_tokens"] = int(prompt_match.group(1))
        metrics["prompt_seconds"] = float(prompt_match.group(2))
        metrics["prompt_tokens_per_second"] = float(prompt_match.group(3))

    if decode_match:
        metrics["decoded_tokens"] = int(decode_match.group(1))
        metrics["decode_seconds"] = float(decode_match.group(2))
        metrics["decode_tokens_per_second"] = float(decode_match.group(3))

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
    timeout_seconds = int(env_str("VLLM_TIMEOUT_SECONDS", "60"))
    build_features = env_str("VLLM_BUILD_FEATURES", "cuda,myelon")
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

    subprocess.run(
        ["cargo", "build", "--bin", "vllm-rs", "--bin", "runner", "--features", build_features],
        cwd=repo_root,
        check=True,
    )

    cases = [
        ("direct", []),
        ("runner", ["--force-runner"]),
        ("myelon", ["--myelon-ipc"]),
    ]

    results = []
    for label, extra_args in cases:
        command = build_command(
            repo_root,
            model_path,
            prompt,
            max_model_len,
            max_tokens,
            seed,
            extra_args,
        )
        results.append(run_case(repo_root, label, command, timeout_seconds))

    report = {
        "model_path": model_path,
        "prompt": prompt,
        "max_model_len": int(max_model_len),
        "max_tokens": int(max_tokens),
        "seed": int(seed),
        "build_features": build_features,
        "results": results,
    }

    direct_response = results[0]["metrics"]["response"]
    report["all_responses_match"] = all(
        result["metrics"]["response"] == direct_response for result in results
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output_path)

    if any(result["exit_code"] != 0 for result in results):
        return 1
    if not report["all_responses_match"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
