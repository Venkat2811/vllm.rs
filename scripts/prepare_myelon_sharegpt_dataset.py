#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    upstream_script = (
        repo_root.parent
        / "vllm"
        / "benchmarks"
        / "multi_turn"
        / "convert_sharegpt_to_openai.py"
    )

    parser = argparse.ArgumentParser(
        description="Prepare a bounded ShareGPT-derived multi-turn dataset using the upstream vLLM converter."
    )
    parser.add_argument("--sharegpt-input", required=True, help="Local ShareGPT JSON file")
    parser.add_argument(
        "--output-file",
        default=str(
            repo_root
            / "artifacts"
            / "b300_benchmarking_2026_04_02"
            / "sharegpt_conv_128.json"
        ),
        help="Output JSON file in OpenAI multi-turn format",
    )
    parser.add_argument("--seed", type=int, default=99)
    parser.add_argument("--max-items", type=int, default=128)
    parser.add_argument("--min-content-len", type=int, default=None)
    parser.add_argument("--max-content-len", type=int, default=None)
    parser.add_argument("--min-turns", type=int, default=None)
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument(
        "--tokenizer-model",
        default=None,
        help="Optional tokenizer model/path for statistics in the upstream converter",
    )
    args = parser.parse_args()

    sharegpt_input = Path(args.sharegpt_input)
    output_file = Path(args.output_file)

    if not upstream_script.is_file():
        print(f"upstream converter not found: {upstream_script}", file=sys.stderr)
        return 1
    if not sharegpt_input.is_file():
        print(f"ShareGPT input not found: {sharegpt_input}", file=sys.stderr)
        return 1

    output_file.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "uv",
        "run",
        "--with",
        "pandas",
        "--with",
        "tqdm",
        "--with",
        "transformers",
        "python3",
        str(upstream_script),
        str(sharegpt_input),
        str(output_file),
        f"--seed={args.seed}",
        f"--max-items={args.max_items}",
    ]
    if args.min_content_len is not None:
        command.append(f"--min-content-len={args.min_content_len}")
    if args.max_content_len is not None:
        command.append(f"--max-content-len={args.max_content_len}")
    if args.min_turns is not None:
        command.append(f"--min-turns={args.min_turns}")
    if args.max_turns is not None:
        command.append(f"--max-turns={args.max_turns}")
    if args.tokenizer_model is not None:
        command.append(f"--model={args.tokenizer_model}")

    subprocess.run(command, cwd=repo_root, check=True)
    print(output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
