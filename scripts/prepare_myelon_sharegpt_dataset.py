#!/usr/bin/env python3
import argparse
import importlib.util
import sys
from pathlib import Path


def load_upstream_module(module_path: Path):
    spec = importlib.util.spec_from_file_location(
        "myelon_upstream_convert_sharegpt_to_openai", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_ascii_only_validator():
    def content_is_valid(
        content: str, min_content_len: int | None, max_content_len: int | None
    ) -> bool:
        if min_content_len and len(content) < min_content_len:
            return False
        if max_content_len and len(content) > max_content_len:
            return False
        return content.isascii()

    return content_is_valid


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
    parser.add_argument(
        "--allow-non-ascii",
        action="store_true",
        help="Keep the upstream converter's non-ASCII behavior instead of the local ASCII-only patch.",
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

    try:
        upstream_module = load_upstream_module(upstream_script)
    except Exception as error:
        print(f"failed to import upstream converter: {error}", file=sys.stderr)
        return 1

    if not args.allow_non_ascii:
        upstream_module.content_is_valid = make_ascii_only_validator()
        print(
            "Patched upstream ShareGPT content filter to keep ASCII-only messages."
        )

    try:
        upstream_module.convert_sharegpt_to_openai(
            args.seed,
            str(sharegpt_input),
            str(output_file),
            args.max_items,
            args.min_content_len,
            args.max_content_len,
            args.min_turns,
            args.max_turns,
            args.tokenizer_model,
        )
    except ImportError as error:
        print(
            "missing dependency while loading the upstream converter; run this script "
            "with pandas, tqdm, and transformers available",
            file=sys.stderr,
        )
        print(error, file=sys.stderr)
        return 1

    print(output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
