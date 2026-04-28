#!/usr/bin/env python3
"""Build long-context ShareGPT prompt buckets by concatenating 1k-token prompts.

The H200 campaign datasets only ship 1k and 2k buckets. Long-context PD benches
need 4k/8k/16k/32k. Each output prompt is built by joining N source prompts with
a separator until the target token count is met. This is synthetic but
deterministic given a seed, and the input distribution stays inside the
ShareGPT register so it doesn't trip safety filters or weird tokenization paths.
"""
import argparse
import json
import random
from pathlib import Path

SEP = "\n\n---\n\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="source jsonl, e.g. sharegpt_1k.jsonl")
    p.add_argument("--target-tokens", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--num-prompts", type=int, default=100)
    p.add_argument("--tolerance", type=float, default=0.10, help="±tolerance fraction around target")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    rng = random.Random(args.seed)
    src_records = []
    with open(args.src) as f:
        for line in f:
            line = line.strip()
            if line:
                src_records.append(json.loads(line))

    rng.shuffle(src_records)
    if not src_records:
        raise SystemExit(f"no records found in {args.src}")

    avg_tokens = sum(r["input_tokens"] for r in src_records) / len(src_records)
    target = args.target_tokens
    lo = int(target * (1 - args.tolerance))
    hi = int(target * (1 + args.tolerance))

    out_records = []
    cursor = 0
    while len(out_records) < args.num_prompts:
        chunks = []
        running_tokens = 0
        # build until in range
        while running_tokens < lo and cursor < len(src_records):
            r = src_records[cursor]
            cursor += 1
            chunks.append(r["prompt"])
            running_tokens += r["input_tokens"]
            # rough: ignore separator's small token cost
        if cursor >= len(src_records):
            cursor = 0
            rng.shuffle(src_records)
        if running_tokens >= lo:
            prompt_text = SEP.join(chunks)
            out_records.append({
                "prompt": prompt_text,
                "input_tokens": running_tokens,  # approximate
                "input_chunks": len(chunks),
                "target_tokens": target,
            })

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for r in out_records:
            f.write(json.dumps(r) + "\n")

    actual = [r["input_tokens"] for r in out_records]
    print(f"wrote {len(out_records)} prompts to {args.out}")
    print(f"  target={target}, range=[{lo}, {hi}]")
    print(f"  actual: min={min(actual)} max={max(actual)} mean={sum(actual)/len(actual):.0f}")


if __name__ == "__main__":
    main()
