#!/usr/bin/env python3
"""Build a multi-turn first-turn prompt bucket by truncating ShareGPT prompts
to 200-500 token range.

For multi-turn benches we want short initial prompts (200-500 tok) so the
conversation accumulates context across rounds rather than being dominated by
turn 1. Output is JSONL with {"prompt": str, "input_tokens": int, "source_tokens": int}.
"""
import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="source JSONL with {'prompt','input_tokens'} records")
    p.add_argument("--out", required=True)
    p.add_argument("--target-min-tokens", type=int, default=200)
    p.add_argument("--target-max-tokens", type=int, default=500)
    p.add_argument("--num-prompts", type=int, default=200)
    p.add_argument("--chars-per-token", type=float, default=4.0,
                   help="rough chars/token for truncation")
    args = p.parse_args()

    out_records = []
    target_chars_max = int(args.target_max_tokens * args.chars_per_token)
    target_chars_min = int(args.target_min_tokens * args.chars_per_token)
    with open(args.src) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            text = (d.get("prompt") or "").strip()
            if not text:
                continue
            if len(text) < target_chars_min:
                continue
            truncated = text[:target_chars_max]
            est_tokens = max(args.target_min_tokens, len(truncated) // 4)
            out_records.append({
                "prompt": truncated,
                "input_tokens": est_tokens,
                "source_tokens": d.get("input_tokens", 0),
            })
            if len(out_records) >= args.num_prompts:
                break

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for r in out_records:
            f.write(json.dumps(r) + "\n")
    if out_records:
        toks = [r["input_tokens"] for r in out_records]
        print(f"wrote {len(out_records)} prompts to {args.out}")
        print(f"  est tokens: min={min(toks)}  mean={sum(toks)/len(toks):.0f}  max={max(toks)}")
    else:
        print(f"WARNING: no records written from {args.src}")


if __name__ == "__main__":
    main()
