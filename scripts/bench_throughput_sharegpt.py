#!/usr/bin/env python3
"""Throughput-mode benchmark for vllm.rs CLI batch path (no HTTP server).

Picks a representative ~target-token ShareGPT prompt, invokes the vllm.rs
binary with `--batch N --prompts P --max-tokens M --num-shards X`, and parses
prompt/decode tokens-per-second from stdout. Repeats with a warmup discard,
reports median + IQR — vllm-bench style.

This is the offline counterpart to bench_stress_sharegpt.py. It exercises only
engine↔runners IPC plus model compute — no HTTP, no PD, no KV transfer. So if
codec/zero-copy/frame-size choices matter anywhere at the application level,
they should show up here.

Variants are selected by passing different binaries (compiled with different
features) and different --myelon-* flags. The script just runs and parses.
"""
import argparse
import json
import random
import re
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path

PROMPT_RE = re.compile(r"Prompt tokens:\s*(\d+)\s+in\s+([\d.]+)s\s+\(([\d.]+)\s+tokens/s\)")
DECODE_RE = re.compile(r"Decoded tokens:\s*(\d+)\s+in\s+([\d.]+)s\s+\(([\d.]+)\s+tokens/s\)")
TOPOLOGY_RE = re.compile(r"Runner topology mode=(\w+)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="vllm.rs CLI batch throughput bench with ShareGPT prompt.")
    p.add_argument("--binary", required=True, help="Path to vllm-rs binary (already built with desired features)")
    p.add_argument("--model-id", required=True, help="HF model id, e.g. Qwen/Qwen3-0.6B")
    p.add_argument("--tokenizer", default=None, help="HF tokenizer id (defaults to --model-id)")
    p.add_argument("--dataset", required=True, help="ShareGPT V3 JSON path")
    p.add_argument("--prompt-target-tok", type=int, default=1024)
    p.add_argument("--prompt-tolerance", type=int, default=128, help="±tokens from target when picking the prompt")
    p.add_argument("--batch", type=int, default=128, help="batch size = clone count of the chosen prompt")
    p.add_argument("--max-tokens", type=int, default=64)
    p.add_argument("--max-model-len", type=int, default=4096)
    p.add_argument("--num-shards", type=int, default=4)
    p.add_argument("--device-ids", type=str, default="0,1,2,3")
    p.add_argument("--dtype", type=str, default="bf16")
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--cuda-compute-cap", type=str, default="120")
    p.add_argument("--myelon-ipc", action="store_true")
    p.add_argument("--myelon-access-mode", choices=["owned", "borrowed", "typed"], default="owned")
    p.add_argument("--myelon-backend", choices=["shm", "mmap"], default="shm")
    p.add_argument("--myelon-busy-spin", action="store_true")
    p.add_argument("--myelon-rpc-depth", type=int, default=None)
    p.add_argument("--myelon-response-depth", type=int, default=None)
    p.add_argument("--warmup-runs", type=int, default=1, help="discarded warmup invocations")
    p.add_argument("--repeat-runs", type=int, default=3, help="measured invocations; reports median + IQR")
    p.add_argument("--per-run-timeout-sec", type=int, default=300)
    p.add_argument("--output-file", required=True, help="aggregate JSON path")
    p.add_argument("--label", type=str, default="run", help="human label for this configuration")
    return p


def load_representative_prompt(args: argparse.Namespace) -> tuple[str, int]:
    from transformers import AutoTokenizer
    tok_id = args.tokenizer or args.model_id
    print(f"[bench] tokenizer {tok_id}", file=sys.stderr)
    tok = AutoTokenizer.from_pretrained(tok_id)
    print(f"[bench] dataset {args.dataset}", file=sys.stderr)
    data = json.load(open(args.dataset, encoding="utf-8"))
    rng = random.Random(args.seed)
    rng.shuffle(data)
    target = args.prompt_target_tok
    tol = args.prompt_tolerance
    best: tuple[int, str] | None = None
    scanned = 0
    for entry in data:
        scanned += 1
        if "conversations" not in entry or len(entry["conversations"]) < 2:
            continue
        first = entry["conversations"][0]
        if first.get("from") not in ("human", "user"):
            continue
        text = first["value"]
        n = len(tok.encode(text))
        if abs(n - target) <= tol:
            best = (n, text)
            break
        if scanned > 20000:
            break
    if best is None:
        raise RuntimeError(
            f"no ShareGPT prompt within ±{tol} of {target} tokens after scanning {scanned}"
        )
    n, text = best
    print(f"[bench] picked prompt at {n} tokens (target {target}±{tol}); scanned {scanned}", file=sys.stderr)
    return text, n


def build_command(args: argparse.Namespace, prompt_text: str) -> list[str]:
    cmd = [
        args.binary,
        "--m", args.model_id,
        "--num-shards", str(args.num_shards),
        "--device-ids", args.device_ids,
        "--max-model-len", str(args.max_model_len),
        "--max-tokens", str(args.max_tokens),
        "--batch", str(args.batch),
        "--dtype", args.dtype,
        "--seed", str(args.seed),
        "--prompts", prompt_text,
    ]
    if args.myelon_ipc:
        cmd += ["--myelon-ipc",
                "--myelon-access-mode", args.myelon_access_mode,
                "--myelon-backend", args.myelon_backend]
        if args.myelon_busy_spin:
            cmd.append("--myelon-busy-spin")
        if args.myelon_rpc_depth is not None:
            cmd += ["--myelon-rpc-depth", str(args.myelon_rpc_depth)]
        if args.myelon_response_depth is not None:
            cmd += ["--myelon-response-depth", str(args.myelon_response_depth)]
    return cmd


def parse_metrics(stdout: str, stderr: str) -> dict:
    combined = stdout + "\n" + stderr
    m = PROMPT_RE.search(combined)
    d = DECODE_RE.search(combined)
    t = TOPOLOGY_RE.search(combined)
    out: dict = {
        "prompt_tokens": int(m.group(1)) if m else None,
        "prompt_seconds": float(m.group(2)) if m else None,
        "prompt_tps": float(m.group(3)) if m else None,
        "decode_tokens": int(d.group(1)) if d else None,
        "decode_seconds": float(d.group(2)) if d else None,
        "decode_tps": float(d.group(3)) if d else None,
        "runner_mode": t.group(1) if t else None,
    }
    return out


def run_once(args: argparse.Namespace, prompt_text: str, label: str) -> dict:
    cmd = build_command(args, prompt_text)
    env = {**__import__("os").environ, "CUDA_COMPUTE_CAP": args.cuda_compute_cap}
    print(f"[bench] {label}: {shlex.join(cmd[:2])} ... ({len(cmd)} args)", file=sys.stderr)
    started = time.perf_counter()
    proc = subprocess.run(
        cmd, capture_output=True, text=True, env=env, timeout=args.per_run_timeout_sec, check=False,
    )
    elapsed = time.perf_counter() - started
    metrics = parse_metrics(proc.stdout, proc.stderr)
    metrics.update({
        "label": label,
        "exit_code": proc.returncode,
        "wall_seconds": round(elapsed, 3),
    })
    return {"metrics": metrics, "stdout": proc.stdout, "stderr": proc.stderr}


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def iqr_range(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    s = sorted(values)
    return s[max(0, len(s) // 4)], s[min(len(s) - 1, (3 * len(s)) // 4)]


def aggregate(measured: list[dict]) -> dict:
    if not measured:
        return {}
    out: dict = {"runs": len(measured)}
    for key in ("prompt_tokens", "prompt_seconds", "prompt_tps", "decode_tokens", "decode_seconds", "decode_tps", "wall_seconds"):
        vals = [r[key] for r in measured if r.get(key) is not None]
        if not vals:
            continue
        q1, q3 = iqr_range(vals)
        out[key] = {
            "median": round(median(vals), 3),
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            "iqr_q1": round(q1, 3),
            "iqr_q3": round(q3, 3),
            "all": [round(v, 3) if isinstance(v, float) else v for v in vals],
        }
    return out


def main() -> int:
    args = build_parser().parse_args()
    if args.warmup_runs < 0 or args.repeat_runs < 1:
        print("--warmup-runs >= 0 and --repeat-runs >= 1 required", file=sys.stderr)
        return 1
    if not Path(args.binary).is_file():
        print(f"binary not found: {args.binary}", file=sys.stderr)
        return 2

    prompt_text, prompt_tokens = load_representative_prompt(args)

    raw: list[dict] = []
    measured: list[dict] = []

    for i in range(args.warmup_runs):
        r = run_once(args, prompt_text, f"warmup_{i + 1}")
        raw.append(r)
        if r["metrics"]["exit_code"] != 0:
            print(f"[bench] warmup {i + 1} failed (exit {r['metrics']['exit_code']})", file=sys.stderr)
            print(r["stderr"][-2000:], file=sys.stderr)
            return 3

    for i in range(args.repeat_runs):
        r = run_once(args, prompt_text, f"measured_{i + 1}")
        raw.append(r)
        if r["metrics"]["exit_code"] != 0:
            print(f"[bench] measured {i + 1} failed (exit {r['metrics']['exit_code']})", file=sys.stderr)
            print(r["stderr"][-2000:], file=sys.stderr)
            return 4
        measured.append(r["metrics"])

    agg = aggregate(measured)

    out = {
        "config": vars(args),
        "prompt_tokens_used": prompt_tokens,
        "aggregate": agg,
        "measured_runs": measured,
        "raw_runs": [{"label": r["metrics"]["label"], "metrics": r["metrics"]} for r in raw],
    }
    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_file).write_text(json.dumps(out, indent=2))

    # human summary
    pt = agg.get("prompt_tps", {})
    dt = agg.get("decode_tps", {})
    ws = agg.get("wall_seconds", {})
    print(
        f"[{args.label} median over {agg['runs']} runs, warmup={args.warmup_runs}]\n"
        f"  prompt tok/s median={pt.get('median')} (IQR {pt.get('iqr_q1')}-{pt.get('iqr_q3')}, all={pt.get('all')})\n"
        f"  decode tok/s median={dt.get('median')} (all={dt.get('all')})\n"
        f"  wall_seconds median={ws.get('median')}s (all={ws.get('all')})\n"
        f"  prompt={prompt_tokens} tok × batch={args.batch} = {prompt_tokens * args.batch} prompt tokens"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
