#!/usr/bin/env python3
import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path

from tabulate import tabulate

from myelon_benchmark_common import build_command, run_case


MODELS = {
    "qwen3_0_6b": {
        "label": "Qwen3-0.6B",
        "model_path": str(
            next(
                (
                    Path.home()
                    / ".cache"
                    / "huggingface"
                    / "hub"
                    / "models--Qwen--Qwen3-0.6B"
                    / "snapshots"
                ).iterdir()
            )
        ),
        "prompt_repetitions": 60,
    },
    "tinyllama_1_1b": {
        "label": "TinyLlama-1.1B",
        "model_path": str(
            next(
                (
                    Path.home()
                    / ".cache"
                    / "huggingface"
                    / "hub"
                    / "models--TinyLlama--TinyLlama-1.1B-Chat-v1.0"
                    / "snapshots"
                ).iterdir()
            )
        ),
        "prompt_repetitions": 40,
    },
}

CODECS = {
    "rkyv": ["metal", "myelon", "codec-rkyv"],
    "flatbuf": ["metal", "myelon", "codec-flatbuf"],
}

CASES = [
    ("socket_runner", ["--num-shards", "1", "--force-runner"]),
    (
        "myelon_shm_owned",
        [
            "--num-shards",
            "1",
            "--myelon-ipc",
            "--myelon-backend",
            "shm",
            "--myelon-access-mode",
            "owned",
        ],
    ),
    (
        "myelon_shm_borrowed",
        [
            "--num-shards",
            "1",
            "--myelon-ipc",
            "--myelon-backend",
            "shm",
            "--myelon-access-mode",
            "borrowed",
        ],
    ),
    (
        "myelon_mmap_owned",
        [
            "--num-shards",
            "1",
            "--myelon-ipc",
            "--myelon-backend",
            "mmap",
            "--myelon-access-mode",
            "owned",
        ],
    ),
    (
        "myelon_mmap_borrowed",
        [
            "--num-shards",
            "1",
            "--myelon-ipc",
            "--myelon-backend",
            "mmap",
            "--myelon-access-mode",
            "borrowed",
        ],
    ),
]

PROMPT_SEED = (
    "Summarize how shared-memory IPC, mmap transports, and zero-copy codecs affect inference "
    "prefill throughput and decode stability on Apple Silicon in practical single-shard setups. "
)


def build_release(repo_root: Path, features: list[str]) -> Path:
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--features",
            ",".join(features),
        ],
        cwd=repo_root,
        check=True,
    )
    return repo_root / "target" / "release" / "vllm-rs"


def make_prompt(repetitions: int) -> str:
    return PROMPT_SEED * repetitions


def summarize_runs(runs: list[dict]) -> dict:
    for run in runs:
        metrics = run["metrics"]
        missing = [
            key
            for key in ("prompt_tokens_per_second", "decode_tokens_per_second", "prompt_seconds")
            if metrics.get(key) is None
        ]
        if missing:
            raise RuntimeError(
                f'case={run["label"]} exited with incomplete metrics: missing {", ".join(missing)}'
            )
    prompt_tps = [run["metrics"]["prompt_tokens_per_second"] for run in runs]
    decode_tps = [run["metrics"]["decode_tokens_per_second"] for run in runs]
    prompt_seconds = [run["metrics"]["prompt_seconds"] for run in runs]
    prompt_tokens = [run["metrics"]["prompt_tokens"] for run in runs]
    decoded_tokens = [run["metrics"]["decoded_tokens"] for run in runs]
    runner_modes = sorted({run["metrics"]["runner_mode"] for run in runs})
    runner_reasons = sorted({run["metrics"]["runner_reason"] for run in runs})
    return {
        "prompt_tokens": prompt_tokens[0],
        "decoded_tokens": decoded_tokens[0],
        "prompt_tokens_per_second_mean": statistics.mean(prompt_tps),
        "prompt_tokens_per_second_stdev": statistics.pstdev(prompt_tps),
        "decode_tokens_per_second_mean": statistics.mean(decode_tps),
        "decode_tokens_per_second_stdev": statistics.pstdev(decode_tps),
        "prompt_seconds_mean": statistics.mean(prompt_seconds),
        "runner_modes": runner_modes,
        "runner_reasons": runner_reasons,
        "myelon_enabled": all(run["metrics"]["myelon_enabled"] for run in runs),
        "runs": runs,
    }


def run_matrix(
    repo_root: Path,
    model_key: str,
    batch_size: int,
    max_model_len: str,
    max_tokens: str,
    repeats: int,
    timeout_seconds: int,
    rpc_depth: str,
    response_depth: str,
    busy_spin: bool,
) -> dict:
    model = MODELS[model_key]
    prompt = make_prompt(model["prompt_repetitions"])
    result = {
        "host": subprocess.check_output(["uname", "-a"], text=True).strip(),
        "model": model_key,
        "model_label": model["label"],
        "model_path": model["model_path"],
        "prompt_repetitions": model["prompt_repetitions"],
        "batch_size": batch_size,
        "max_model_len": max_model_len,
        "max_tokens": max_tokens,
        "repeats": repeats,
        "codecs": {},
    }

    for codec, features in CODECS.items():
        binary_path = build_release(repo_root, features)
        codec_rows = {}
        for case_label, extra_args in CASES:
            runs = []
            for repeat in range(repeats):
                command = build_command(
                    repo_root=repo_root,
                    binary_path=binary_path,
                    model_path=model["model_path"],
                    prompt=prompt,
                    batch_size=batch_size,
                    max_model_len=max_model_len,
                    max_tokens=max_tokens,
                    seed=str(123 + repeat),
                    device_ids=None,
                    myelon_rpc_depth=rpc_depth,
                    myelon_response_depth=response_depth,
                    myelon_busy_spin=busy_spin,
                    extra_args=extra_args,
                )
                runs.append(run_case(repo_root, case_label, command, timeout_seconds))
            codec_rows[case_label] = summarize_runs(runs)
        result["codecs"][codec] = codec_rows
    return result


def print_summary(result: dict) -> None:
    rows = []
    for codec, cases in result["codecs"].items():
        for case_label, summary in cases.items():
            rows.append(
                [
                    result["model_label"],
                    codec,
                    case_label,
                    f'{summary["prompt_tokens"]}',
                    f'{summary["prompt_tokens_per_second_mean"]:.2f} ± {summary["prompt_tokens_per_second_stdev"]:.2f}',
                    f'{summary["decode_tokens_per_second_mean"]:.2f} ± {summary["decode_tokens_per_second_stdev"]:.2f}',
                    f'{summary["prompt_seconds_mean"]:.2f}',
                    ",".join(summary["runner_modes"]),
                    ",".join(summary["runner_reasons"]),
                ]
            )
    print(
        tabulate(
            rows,
            headers=[
                "model",
                "codec",
                "case",
                "prompt tok",
                "prompt tok/s",
                "decode tok/s",
                "prompt s",
                "runner mode",
                "runner reason",
            ],
            tablefmt="rounded_outline",
            stralign="left",
            numalign="right",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["all", *MODELS.keys()], default="all")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-model-len", default="2048")
    parser.add_argument("--max-tokens", default="32")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--myelon-rpc-depth", default="8192")
    parser.add_argument("--myelon-response-depth", default="8192")
    parser.add_argument("--myelon-busy-spin", action="store_true")
    parser.add_argument(
        "--json-out",
        default=f"/tmp/vllm_myelon_codec_backend_access_matrix_{int(time.time())}.json",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    selected_models = MODELS.keys() if args.model == "all" else [args.model]
    results = []
    for model_key in selected_models:
        result = run_matrix(
            repo_root=repo_root,
            model_key=model_key,
            batch_size=args.batch_size,
            max_model_len=args.max_model_len,
            max_tokens=args.max_tokens,
            repeats=args.repeats,
            timeout_seconds=args.timeout_seconds,
            rpc_depth=args.myelon_rpc_depth,
            response_depth=args.myelon_response_depth,
            busy_spin=args.myelon_busy_spin,
        )
        results.append(result)
        print_summary(result)
        print()

    payload = {"results": results}
    Path(args.json_out).write_text(json.dumps(payload, indent=2))
    print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
