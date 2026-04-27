#!/usr/bin/env python3
"""Tokenize ShareGPT V3 with the target model's tokenizer and bucket by length.

Buckets:
  - 1k: 1024 <= input_tokens < 2048
  - 2k: 2048 <= input_tokens < 4096   (cap at 4096 to fit 4K context window)

Output JSONL records: {"prompt": str, "input_tokens": int}

Uses the *fast* Rust tokenizer + batched encoding for speed. ~94K conversations
in V3; full pass takes a couple of minutes.
"""
import argparse
import json
import sys
import time
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="/root/.cache/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json")
    p.add_argument("--tokenizer", default="Qwen/Qwen3-30B-A3B")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--bucket-1k", nargs=2, type=int, default=[1024, 2048],
                   metavar=("LO", "HI"), help="[lo, hi) token range for 1k bucket")
    p.add_argument("--bucket-2k", nargs=2, type=int, default=[2048, 4096],
                   metavar=("LO", "HI"), help="[lo, hi) token range for 2k bucket")
    p.add_argument("--batch-size", type=int, default=512, help="tokenize batch size")
    p.add_argument("--max-prompts-per-bucket", type=int, default=2000,
                   help="cap to keep buckets manageable; 200 reqs * 10 concurrencies = need >2000 distinct")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[prep] tokenizer: {args.tokenizer}", file=sys.stderr)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.tokenizer, use_fast=True)
    print(f"[prep] is_fast={tok.is_fast}", file=sys.stderr)

    print(f"[prep] loading {args.dataset}", file=sys.stderr)
    t0 = time.perf_counter()
    with open(args.dataset, encoding="utf-8") as f:
        data = json.load(f)
    print(f"[prep] loaded {len(data)} conversations in {time.perf_counter()-t0:.1f}s", file=sys.stderr)

    # Extract first human turn from each conversation
    prompts: list[str] = []
    for conv in data:
        convs = conv.get("conversations", [])
        if not convs:
            continue
        first = convs[0]
        if first.get("from") not in ("human", "user"):
            continue
        text = first.get("value")
        if isinstance(text, str) and text.strip():
            prompts.append(text)
    print(f"[prep] extracted {len(prompts)} first-human prompts", file=sys.stderr)

    # Batch tokenize
    bucket_1k_lo, bucket_1k_hi = args.bucket_1k
    bucket_2k_lo, bucket_2k_hi = args.bucket_2k
    bucket_1k: list[dict] = []
    bucket_2k: list[dict] = []

    t0 = time.perf_counter()
    target_total = args.max_prompts_per_bucket * 2 + 100
    for i in range(0, len(prompts), args.batch_size):
        batch = prompts[i : i + args.batch_size]
        enc = tok(batch, add_special_tokens=False, return_attention_mask=False, return_token_type_ids=False)
        for prompt, ids in zip(batch, enc["input_ids"]):
            n = len(ids)
            entry = {"prompt": prompt, "input_tokens": n}
            if bucket_1k_lo <= n < bucket_1k_hi and len(bucket_1k) < args.max_prompts_per_bucket:
                bucket_1k.append(entry)
            elif bucket_2k_lo <= n < bucket_2k_hi and len(bucket_2k) < args.max_prompts_per_bucket:
                bucket_2k.append(entry)
        if (i // args.batch_size) % 20 == 0:
            elapsed = time.perf_counter() - t0
            print(f"[prep] scanned {i + len(batch)}/{len(prompts)}  1k={len(bucket_1k)}  2k={len(bucket_2k)}  elapsed={elapsed:.1f}s",
                  file=sys.stderr)
        # Early exit when both buckets full
        if len(bucket_1k) >= args.max_prompts_per_bucket and len(bucket_2k) >= args.max_prompts_per_bucket:
            print(f"[prep] both buckets full at scan {i + len(batch)}/{len(prompts)}", file=sys.stderr)
            break

    elapsed = time.perf_counter() - t0
    print(f"[prep] tokenized in {elapsed:.1f}s; 1k={len(bucket_1k)} 2k={len(bucket_2k)}", file=sys.stderr)

    # Write JSONL
    for name, bucket, (lo, hi) in [
        ("1k", bucket_1k, (bucket_1k_lo, bucket_1k_hi)),
        ("2k", bucket_2k, (bucket_2k_lo, bucket_2k_hi)),
    ]:
        out_path = out_dir / f"sharegpt_{name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for e in bucket:
                f.write(json.dumps(e) + "\n")
        # Summary stats
        if bucket:
            ns = sorted(e["input_tokens"] for e in bucket)
            n_min, n_max = ns[0], ns[-1]
            n_med = ns[len(ns) // 2]
            print(f"[prep] {out_path}: {len(bucket)} prompts  range=[{n_min}, {n_max}]  median={n_med}  spec=[{lo}, {hi})",
                  file=sys.stderr)
        else:
            print(f"[prep] {out_path}: empty (no prompts in [{lo}, {hi}))", file=sys.stderr)

    # Manifest
    manifest = {
        "source_dataset": args.dataset,
        "tokenizer": args.tokenizer,
        "tokenizer_is_fast": tok.is_fast,
        "scanned_conversations": len(data),
        "extracted_first_human_prompts": len(prompts),
        "buckets": {
            "1k": {"range": [bucket_1k_lo, bucket_1k_hi], "count": len(bucket_1k),
                    "path": str(out_dir / "sharegpt_1k.jsonl")},
            "2k": {"range": [bucket_2k_lo, bucket_2k_hi], "count": len(bucket_2k),
                    "path": str(out_dir / "sharegpt_2k.jsonl")},
        },
        "max_prompts_per_bucket": args.max_prompts_per_bucket,
        "seed": args.seed,
    }
    (out_dir / "sharegpt_buckets_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[prep] manifest written to {out_dir / 'sharegpt_buckets_manifest.json'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
