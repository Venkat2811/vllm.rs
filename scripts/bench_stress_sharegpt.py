#!/usr/bin/env python3
"""Stress benchmark client for an OpenAI-compatible chat server.

Loads ShareGPT prompts filtered to a target token-length range, then issues
requests under a configurable load profile:
  * --request-rate λ : open-loop Poisson arrivals at λ req/s (--request-rate 0 = closed-loop)
  * --concurrency N  : max in-flight requests (caps the open-loop, drives the closed-loop)
  * --duration-sec or --num-requests : termination

Per-request we record: arrival/dispatch/first-token/finish timestamps, output token
count, success flag. Aggregates p50/p95/p99 TTFT and end-to-end latency, throughput
(req/s and output-tokens/s), and success rate.

Output JSON shape:
{
  "config": { ... },
  "summary": { ttft p50/95/99, latency p50/95/99, req/s, out_tok/s, success_rate, ... },
  "requests": [ {arrival_s, dispatch_s, ttft_ms, latency_ms, output_tokens, success, error}, ... ]
}
"""
import argparse
import asyncio
import json
import random
import statistics
import sys
import time
from pathlib import Path

import aiohttp
from transformers import AutoTokenizer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ShareGPT-driven stress benchmark.")
    p.add_argument("--url", required=True, help="Base server URL, e.g. http://127.0.0.1:8000")
    p.add_argument("--served-model-name", required=True)
    p.add_argument("--tokenizer", required=True, help="HF tokenizer id (used to filter prompt length)")
    p.add_argument("--dataset", required=True, help="ShareGPT V3 JSON path")
    p.add_argument("--prompt-min-tok", type=int, default=800)
    p.add_argument("--prompt-max-tok", type=int, default=1200)
    p.add_argument("--max-tokens", type=int, default=64, help="response token cap")
    p.add_argument("--concurrency", type=int, default=64, help="max in-flight requests")
    p.add_argument(
        "--request-rate",
        type=float,
        default=0.0,
        help="open-loop Poisson lambda req/s; 0 = closed-loop (semaphore-bounded)",
    )
    term = p.add_mutually_exclusive_group(required=True)
    term.add_argument("--num-requests", type=int)
    term.add_argument("--duration-sec", type=float)
    p.add_argument("--request-timeout-sec", type=float, default=120.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-file", required=True)
    p.add_argument("--no-stream", action="store_true")
    p.add_argument("--prompt-pool-size", type=int, default=500, help="cap on filtered prompts to use")
    p.add_argument(
        "--warmup-runs",
        type=int,
        default=0,
        help="number of full benchmark passes to discard for warmup before measurement",
    )
    p.add_argument(
        "--repeat-runs",
        type=int,
        default=1,
        help="number of measured benchmark passes; reports median + IQR across them",
    )
    return p


def load_prompt_pool(args: argparse.Namespace) -> list[str]:
    print(f"[bench] loading tokenizer {args.tokenizer}", file=sys.stderr)
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    print(f"[bench] loading dataset {args.dataset}", file=sys.stderr)
    with open(args.dataset, encoding="utf-8") as f:
        data = json.load(f)
    rng = random.Random(args.seed)
    rng.shuffle(data)
    pool: list[str] = []
    scanned = 0
    for entry in data:
        scanned += 1
        if "conversations" not in entry or len(entry["conversations"]) < 2:
            continue
        first = entry["conversations"][0]
        if first.get("from") not in ("human", "user"):
            continue
        prompt = first["value"]
        n = len(tok.encode(prompt))
        if args.prompt_min_tok <= n <= args.prompt_max_tok:
            pool.append(prompt)
            if len(pool) >= args.prompt_pool_size:
                break
        if scanned > 30000 and not pool:
            break
    if not pool:
        raise RuntimeError(
            f"no prompts in [{args.prompt_min_tok}, {args.prompt_max_tok}] tokens after scanning {scanned}"
        )
    print(f"[bench] prompt pool: {len(pool)} prompts (scanned {scanned})", file=sys.stderr)
    return pool


async def one_request(
    session: aiohttp.ClientSession,
    *,
    url: str,
    model: str,
    prompt_text: str,
    max_tokens: int,
    timeout_seconds: float,
    stream: bool,
    arrival_s: float,
    bench_start_s: float,
) -> dict:
    rec: dict = {
        "arrival_s": round(arrival_s - bench_start_s, 4),
        "dispatch_s": None,
        "ttft_ms": None,
        "latency_ms": None,
        "output_tokens": 0,
        "output_chunks": 0,
        "success": False,
        "error": None,
    }
    dispatch_t = time.perf_counter()
    rec["dispatch_s"] = round(dispatch_t - bench_start_s, 4)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": max_tokens,
        "stream": stream,
    }
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    try:
        async with session.post(
            f"{url.rstrip('/')}/v1/chat/completions",
            json=payload,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            if stream:
                async for raw in response.content:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    body = line[len("data:"):].strip()
                    if body == "[DONE]":
                        break
                    msg = json.loads(body)
                    choices = msg.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        if rec["ttft_ms"] is None:
                            rec["ttft_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
                        rec["output_chunks"] += 1
                        rec["output_tokens"] += 1
            else:
                msg = await response.json()
                choices = msg.get("choices", [])
                content = (choices[0].get("message", {}).get("content", "") if choices else "")
                if content:
                    rec["output_tokens"] = max(1, len(content) // 4)  # rough
                rec["ttft_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
        rec["latency_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
        if rec["ttft_ms"] is None:
            rec["ttft_ms"] = rec["latency_ms"]
        rec["success"] = True
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["latency_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
    return rec


async def closed_loop(args: argparse.Namespace, prompts: list[str]) -> tuple[list[dict], float]:
    sem = asyncio.Semaphore(args.concurrency)
    bench_start = time.perf_counter()
    rng = random.Random(args.seed + 1)
    done: list[dict] = []

    async def worker(i: int, sess: aiohttp.ClientSession) -> None:
        async with sem:
            arr = time.perf_counter()
            rec = await one_request(
                sess,
                url=args.url,
                model=args.served_model_name,
                prompt_text=prompts[rng.randrange(len(prompts))],
                max_tokens=args.max_tokens,
                timeout_seconds=args.request_timeout_sec,
                stream=not args.no_stream,
                arrival_s=arr,
                bench_start_s=bench_start,
            )
            done.append(rec)

    async with aiohttp.ClientSession() as sess:
        if args.num_requests:
            await asyncio.gather(*(worker(i, sess) for i in range(args.num_requests)))
        else:
            tasks: list[asyncio.Task] = []
            i = 0
            while time.perf_counter() - bench_start < args.duration_sec:
                tasks.append(asyncio.create_task(worker(i, sess)))
                i += 1
                # let semaphore pace dispatch — yield so completed tasks free slots
                await asyncio.sleep(0)
            await asyncio.gather(*tasks)
    return done, time.perf_counter() - bench_start


async def open_loop(args: argparse.Namespace, prompts: list[str]) -> tuple[list[dict], float]:
    sem = asyncio.Semaphore(args.concurrency)
    bench_start = time.perf_counter()
    rng = random.Random(args.seed + 1)
    done: list[dict] = []
    pending: list[asyncio.Task] = []
    rate = args.request_rate

    async def fire(prompt: str, sess: aiohttp.ClientSession, arr: float) -> None:
        async with sem:
            rec = await one_request(
                sess,
                url=args.url,
                model=args.served_model_name,
                prompt_text=prompt,
                max_tokens=args.max_tokens,
                timeout_seconds=args.request_timeout_sec,
                stream=not args.no_stream,
                arrival_s=arr,
                bench_start_s=bench_start,
            )
            done.append(rec)

    async with aiohttp.ClientSession() as sess:
        if args.num_requests:
            n = 0
            while n < args.num_requests:
                arr = time.perf_counter()
                pending.append(asyncio.create_task(fire(prompts[rng.randrange(len(prompts))], sess, arr)))
                n += 1
                if n < args.num_requests:
                    delay = rng.expovariate(rate)
                    await asyncio.sleep(delay)
            await asyncio.gather(*pending)
        else:
            while time.perf_counter() - bench_start < args.duration_sec:
                arr = time.perf_counter()
                pending.append(asyncio.create_task(fire(prompts[rng.randrange(len(prompts))], sess, arr)))
                delay = rng.expovariate(rate)
                await asyncio.sleep(delay)
            await asyncio.gather(*pending)
    return done, time.perf_counter() - bench_start


def percentile(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * q))]


def summarize(samples: list[dict], runtime_s: float, args: argparse.Namespace) -> dict:
    ok = [s for s in samples if s["success"]]
    fail = len(samples) - len(ok)
    ttft = [float(s["ttft_ms"]) for s in ok if s["ttft_ms"] is not None]
    lat = [float(s["latency_ms"]) for s in ok if s["latency_ms"] is not None]
    tot_out = sum(int(s["output_tokens"]) for s in ok)
    return {
        "runtime_s": round(runtime_s, 3),
        "total_requests": len(samples),
        "successful_requests": len(ok),
        "failed_requests": fail,
        "success_rate": round(len(ok) / len(samples), 4) if samples else 0.0,
        "req_per_s": round(len(ok) / runtime_s, 3) if runtime_s > 0 else 0.0,
        "output_tok_per_s": round(tot_out / runtime_s, 3) if runtime_s > 0 else 0.0,
        "ttft_ms": {
            "min": round(min(ttft), 2) if ttft else None,
            "p50": round(percentile(ttft, 0.50), 2) if ttft else None,
            "p95": round(percentile(ttft, 0.95), 2) if ttft else None,
            "p99": round(percentile(ttft, 0.99), 2) if ttft else None,
            "max": round(max(ttft), 2) if ttft else None,
            "mean": round(statistics.mean(ttft), 2) if ttft else None,
        },
        "latency_ms": {
            "min": round(min(lat), 2) if lat else None,
            "p50": round(percentile(lat, 0.50), 2) if lat else None,
            "p95": round(percentile(lat, 0.95), 2) if lat else None,
            "p99": round(percentile(lat, 0.99), 2) if lat else None,
            "max": round(max(lat), 2) if lat else None,
            "mean": round(statistics.mean(lat), 2) if lat else None,
        },
    }


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


def aggregate_summaries(summaries: list[dict]) -> dict:
    """Aggregate per-run summaries into median + IQR across runs (vllm-bench style)."""
    if not summaries:
        return {}
    out: dict = {"runs": len(summaries)}
    scalar_keys = ["req_per_s", "output_tok_per_s", "success_rate", "runtime_s"]
    for key in scalar_keys:
        vals = [s[key] for s in summaries if s.get(key) is not None]
        if not vals:
            continue
        q1, q3 = iqr_range(vals)
        out[key] = {
            "median": round(median(vals), 3),
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            "iqr_q1": round(q1, 3),
            "iqr_q3": round(q3, 3),
            "all": [round(v, 3) for v in vals],
        }
    for bucket in ("ttft_ms", "latency_ms"):
        out[bucket] = {}
        for stat in ("p50", "p95", "p99", "mean", "max"):
            vals = [s[bucket][stat] for s in summaries if s.get(bucket, {}).get(stat) is not None]
            if not vals:
                continue
            q1, q3 = iqr_range(vals)
            out[bucket][stat] = {
                "median": round(median(vals), 2),
                "iqr_q1": round(q1, 2),
                "iqr_q3": round(q3, 2),
                "all": [round(v, 2) for v in vals],
            }
    return out


async def run_one_pass(args: argparse.Namespace, pool: list[str]) -> tuple[list[dict], float]:
    if args.request_rate > 0:
        return await open_loop(args, pool)
    return await closed_loop(args, pool)


def main() -> int:
    args = build_parser().parse_args()
    if args.warmup_runs < 0 or args.repeat_runs < 1:
        print("--warmup-runs >= 0 and --repeat-runs >= 1 required", file=sys.stderr)
        return 1
    pool = load_prompt_pool(args)

    # Discard warmup passes
    for i in range(args.warmup_runs):
        print(f"[bench] warmup pass {i + 1}/{args.warmup_runs}", file=sys.stderr)
        _ = asyncio.run(run_one_pass(args, pool))

    # Measured passes
    measured_summaries: list[dict] = []
    measured_runs: list[dict] = []
    for i in range(args.repeat_runs):
        print(f"[bench] measured pass {i + 1}/{args.repeat_runs}", file=sys.stderr)
        samples, runtime = asyncio.run(run_one_pass(args, pool))
        s = summarize(samples, runtime, args)
        measured_summaries.append(s)
        measured_runs.append({"summary": s, "requests": samples})

    aggregate = aggregate_summaries(measured_summaries)

    out = {
        "config": vars(args),
        "aggregate": aggregate,
        "per_run_summaries": measured_summaries,
        "prompt_pool_size_used": len(pool),
        "runs": measured_runs,
    }
    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_file).write_text(json.dumps(out, indent=2))

    # Human summary — show median + IQR if multi-run, single-run otherwise
    if args.repeat_runs == 1:
        s = measured_summaries[0]
        print(
            f"req/s={s['req_per_s']:.2f}  out_tok/s={s['output_tok_per_s']:.1f}  "
            f"success={s['successful_requests']}/{s['total_requests']} ({s['success_rate']*100:.1f}%)\n"
            f"  TTFT  ms p50={s['ttft_ms']['p50']} p95={s['ttft_ms']['p95']} p99={s['ttft_ms']['p99']} max={s['ttft_ms']['max']}\n"
            f"  Latency ms p50={s['latency_ms']['p50']} p95={s['latency_ms']['p95']} p99={s['latency_ms']['p99']} max={s['latency_ms']['max']}\n"
            f"  runtime={s['runtime_s']:.2f}s"
        )
    else:
        rps = aggregate["req_per_s"]
        ots = aggregate["output_tok_per_s"]
        ttft_p50 = aggregate["ttft_ms"]["p50"]
        ttft_p99 = aggregate["ttft_ms"]["p99"]
        lat_p50 = aggregate["latency_ms"]["p50"]
        lat_p99 = aggregate["latency_ms"]["p99"]
        rt = aggregate["runtime_s"]
        print(
            f"[median over {aggregate['runs']} runs, warmup={args.warmup_runs}]\n"
            f"  req/s    median={rps['median']} (IQR {rps['iqr_q1']}-{rps['iqr_q3']}, all={rps['all']})\n"
            f"  out_tok/s median={ots['median']} (all={ots['all']})\n"
            f"  TTFT p50  median={ttft_p50['median']}ms (IQR {ttft_p50['iqr_q1']}-{ttft_p50['iqr_q3']})\n"
            f"  TTFT p99  median={ttft_p99['median']}ms (IQR {ttft_p99['iqr_q1']}-{ttft_p99['iqr_q3']})\n"
            f"  Lat  p50  median={lat_p50['median']}ms\n"
            f"  Lat  p99  median={lat_p99['median']}ms\n"
            f"  runtime/run median={rt['median']}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
