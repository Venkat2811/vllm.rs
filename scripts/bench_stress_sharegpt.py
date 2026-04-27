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
    p.add_argument("--tokenizer", default=None, help="HF tokenizer id (only needed when filtering raw --dataset)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--dataset", help="ShareGPT V3 JSON path; will be tokenized + filtered in-process")
    src.add_argument("--prompts-file", help="Pre-bucketed JSONL with {\"prompt\": str, \"input_tokens\": int} records")
    p.add_argument("--prompt-min-tok", type=int, default=800, help="only used with --dataset")
    p.add_argument("--prompt-max-tok", type=int, default=1200, help="only used with --dataset")
    p.add_argument("--max-tokens", type=int, default=64, help="response token cap")
    p.add_argument("--concurrency", type=int, default=64, help="max in-flight requests (vllm calls this --max-concurrency)")
    p.add_argument("--max-concurrency", type=int, default=None, help="alias for --concurrency (vllm-bench compat)")
    p.add_argument(
        "--request-rate",
        type=float,
        default=0.0,
        help="open-loop arrival rate req/s; 0 = closed-loop persistent workers; inf = fire all immediately",
    )
    p.add_argument(
        "--burstiness",
        type=float,
        default=1.0,
        help="gamma shape factor for inter-arrival times. 1.0 = Poisson (default). <1 burstier; >1 more uniform; inf = constant 1/rate.",
    )
    p.add_argument(
        "--ramp-up-strategy",
        choices=["linear", "exponential"],
        default=None,
        help="ramp request rate over the duration of the cell (open-loop only)",
    )
    p.add_argument("--ramp-up-start-rps", type=float, default=None)
    p.add_argument("--ramp-up-end-rps", type=float, default=None)
    p.add_argument(
        "--goodput",
        action="append",
        default=[],
        metavar="METRIC:THRESHOLD_MS",
        help="SLO goal, e.g. --goodput ttft:500 --goodput tpot:50. Goodput = fraction of requests meeting all goals.",
    )
    term = p.add_mutually_exclusive_group(required=True)
    term.add_argument("--num-requests", type=int)
    term.add_argument("--duration-sec", type=float)
    p.add_argument("--request-timeout-sec", type=float, default=120.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-file", required=True)
    p.add_argument("--no-stream", action="store_true")
    p.add_argument("--prompt-pool-size", type=int, default=2000, help="cap on prompts loaded into pool")
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
    # Fast path: pre-bucketed JSONL (no tokenizer, no filter)
    if args.prompts_file:
        path = args.prompts_file
        print(f"[bench] loading prompts JSONL {path}", file=sys.stderr)
        pool: list[str] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                prompt = rec.get("prompt")
                if isinstance(prompt, str) and prompt.strip():
                    pool.append(prompt)
                if len(pool) >= args.prompt_pool_size:
                    break
        if not pool:
            raise RuntimeError(f"no prompts loaded from {path}")
        rng = random.Random(args.seed)
        rng.shuffle(pool)
        print(f"[bench] prompt pool: {len(pool)} prompts (from JSONL)", file=sys.stderr)
        return pool

    # Slow path: raw ShareGPT JSON, tokenize and filter in-process
    if not args.tokenizer:
        raise RuntimeError("--tokenizer required when using --dataset (raw ShareGPT JSON)")
    print(f"[bench] loading tokenizer {args.tokenizer}", file=sys.stderr)
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    print(f"[bench] loading dataset {args.dataset}", file=sys.stderr)
    with open(args.dataset, encoding="utf-8") as f:
        data = json.load(f)
    rng = random.Random(args.seed)
    rng.shuffle(data)
    pool = []
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
        "tpot_ms": None,           # mean inter-token latency (excluding TTFT)
        "itl_ms": [],              # full list of per-token deltas (post-first-token)
        "latency_ms": None,        # E2E latency
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
                last_token_t = None
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
                        now = time.perf_counter()
                        if rec["ttft_ms"] is None:
                            rec["ttft_ms"] = round((now - dispatch_t) * 1000.0, 3)
                            last_token_t = now
                        else:
                            # Inter-token latency for this chunk (each streamed delta = 1 token)
                            rec["itl_ms"].append(round((now - last_token_t) * 1000.0, 3))
                            last_token_t = now
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
        # TPOT = mean ITL when we have post-first-token tokens; otherwise unset
        if rec["itl_ms"]:
            rec["tpot_ms"] = round(sum(rec["itl_ms"]) / len(rec["itl_ms"]), 3)
        rec["success"] = True
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["latency_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
    return rec


async def closed_loop(args: argparse.Namespace, prompts: list[str]) -> tuple[list[dict], float]:
    bench_start = time.perf_counter()
    rng = random.Random(args.seed + 1)
    done: list[dict] = []
    cap = args.max_concurrency if args.max_concurrency else args.concurrency

    async def fire_one(sess: aiohttp.ClientSession) -> None:
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

    async def worker_loop(sess: aiohttp.ClientSession) -> None:
        # one persistent worker — fires sequential requests until duration expires
        while time.perf_counter() - bench_start < args.duration_sec:
            await fire_one(sess)

    async with aiohttp.ClientSession() as sess:
        if args.num_requests:
            # fixed total: spawn N tasks with cap = concurrency (semaphore-bounded)
            sem = asyncio.Semaphore(cap)
            async def capped(i: int) -> None:
                async with sem:
                    await fire_one(sess)
            await asyncio.gather(*(capped(i) for i in range(args.num_requests)))
        else:
            # duration-bounded: spawn exactly `concurrency` persistent workers
            await asyncio.gather(*(worker_loop(sess) for _ in range(cap)))
    return done, time.perf_counter() - bench_start


def _compute_delay_seq(
    rng: random.Random,
    n_requests: int,
    rate: float,
    burstiness: float,
    ramp_up: tuple[str, float, float] | None,
) -> list[float]:
    """Pre-compute inter-arrival delays for N requests (vllm bench-serve pattern).

    With burstiness=1 → exponential (Poisson). burstiness=inf → constant 1/rate.
    Otherwise gamma(burstiness, 1/(rate*burstiness)).
    With ramp-up: rate varies linearly or exponentially across the request index.
    """
    # Early-return zero-delays only when neither static rate nor ramp-up is providing arrivals
    if ramp_up is None and (rate == float("inf") or rate <= 0):
        return [0.0] * n_requests
    delays: list[float] = []
    for i in range(n_requests):
        if ramp_up is not None:
            strategy, start_rps, end_rps = ramp_up
            progress = i / max(n_requests - 1, 1)
            if strategy == "linear":
                cur_rate = start_rps + (end_rps - start_rps) * progress
            else:  # exponential
                ratio = end_rps / max(start_rps, 1e-9)
                cur_rate = start_rps * (ratio ** progress)
        else:
            cur_rate = rate
        if cur_rate == float("inf") or cur_rate <= 0:
            delays.append(0.0)
        elif burstiness == float("inf"):
            delays.append(1.0 / cur_rate)
        elif burstiness == 1.0:
            delays.append(rng.expovariate(cur_rate))
        else:
            theta = 1.0 / (cur_rate * burstiness)
            delays.append(rng.gammavariate(burstiness, theta))
    return delays


async def open_loop(args: argparse.Namespace, prompts: list[str]) -> tuple[list[dict], float]:
    cap = args.max_concurrency if args.max_concurrency else args.concurrency
    sem = asyncio.Semaphore(cap)
    bench_start = time.perf_counter()
    rng = random.Random(args.seed + 1)
    done: list[dict] = []
    pending: list[asyncio.Task] = []
    rate = args.request_rate
    ramp_up = None
    if args.ramp_up_strategy is not None:
        if args.ramp_up_start_rps is None or args.ramp_up_end_rps is None:
            raise RuntimeError("--ramp-up-strategy requires --ramp-up-start-rps and --ramp-up-end-rps")
        ramp_up = (args.ramp_up_strategy, args.ramp_up_start_rps, args.ramp_up_end_rps)

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
            # Pre-compute delays for the entire request stream — matches vllm bench serve.
            delays = _compute_delay_seq(rng, args.num_requests, rate, args.burstiness, ramp_up)
            for i in range(args.num_requests):
                arr = time.perf_counter()
                pending.append(asyncio.create_task(
                    fire(prompts[rng.randrange(len(prompts))], sess, arr)
                ))
                if delays[i] > 0:
                    await asyncio.sleep(delays[i])
            await asyncio.gather(*pending)
        else:
            # Duration-bounded: same delay distribution, computed on-the-fly.
            while time.perf_counter() - bench_start < args.duration_sec:
                arr = time.perf_counter()
                pending.append(asyncio.create_task(
                    fire(prompts[rng.randrange(len(prompts))], sess, arr)
                ))
                # Single-element delay using the same logic
                d = _compute_delay_seq(rng, 1, rate, args.burstiness, None)[0]
                if d > 0:
                    await asyncio.sleep(d)
            await asyncio.gather(*pending)
    return done, time.perf_counter() - bench_start


def percentile(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * q))]


# vllm-style percentiles: mean, std, median, p25, p50, p75, p90, p95, p99, p99.9
_VLLM_PERCENTILES = [0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999]


def _full_stats(vals: list[float]) -> dict | None:
    if not vals:
        return None
    out = {
        "n": len(vals),
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "mean": round(statistics.mean(vals), 3),
        "std": round(statistics.stdev(vals), 3) if len(vals) > 1 else 0.0,
        "median": round(statistics.median(vals), 3),
    }
    for q in _VLLM_PERCENTILES:
        label = f"p{int(q * 100):d}" if q < 0.99 or q == 0.99 else "p999"
        if q == 0.99:
            label = "p99"
        elif q == 0.999:
            label = "p999"
        out[label] = round(percentile(vals, q), 3)
    return out


def _parse_goodput(specs: list[str]) -> dict[str, float]:
    """Parse --goodput METRIC:THRESHOLD args into {metric: threshold_ms} dict.
    Supported metrics: ttft, tpot, itl, e2e (latency), all in ms.
    """
    out: dict[str, float] = {}
    for spec in specs:
        if ":" not in spec:
            raise RuntimeError(f"--goodput requires METRIC:THRESHOLD, got {spec!r}")
        m, t = spec.split(":", 1)
        m = m.strip().lower()
        if m not in ("ttft", "tpot", "itl", "e2e", "latency"):
            raise RuntimeError(f"--goodput unknown metric {m!r}; use ttft|tpot|itl|e2e")
        if m == "latency":
            m = "e2e"
        out[m] = float(t)
    return out


def _meets_goodput(rec: dict, goals: dict[str, float]) -> bool:
    """A request meets goodput iff every named metric is ≤ its threshold."""
    if not goals:
        return True
    for metric, threshold in goals.items():
        if metric == "ttft":
            v = rec.get("ttft_ms")
        elif metric == "tpot":
            v = rec.get("tpot_ms")
        elif metric == "itl":
            # vllm uses max ITL per request for the SLO check
            itl = rec.get("itl_ms") or []
            v = max(itl) if itl else None
        else:  # e2e
            v = rec.get("latency_ms")
        if v is None or v > threshold:
            return False
    return True


def summarize(samples: list[dict], runtime_s: float, args: argparse.Namespace) -> dict:
    ok = [s for s in samples if s["success"]]
    fail = len(samples) - len(ok)
    ttft = [float(s["ttft_ms"]) for s in ok if s.get("ttft_ms") is not None]
    tpot = [float(s["tpot_ms"]) for s in ok if s.get("tpot_ms") is not None]
    # ITL is per-token, flattened across all requests
    itl_flat: list[float] = []
    for s in ok:
        for v in s.get("itl_ms", []) or []:
            itl_flat.append(float(v))
    lat = [float(s["latency_ms"]) for s in ok if s.get("latency_ms") is not None]
    tot_out = sum(int(s["output_tokens"]) for s in ok)
    # Input throughput needs prompt token counts; we don't have them here unless
    # prompts were pre-tokenized. Skip for now; can be added when JSONL carries input_tokens.
    goals = _parse_goodput(args.goodput) if hasattr(args, "goodput") else {}
    good = sum(1 for s in ok if _meets_goodput(s, goals)) if goals else None

    return {
        "runtime_s": round(runtime_s, 3),
        "total_requests": len(samples),
        "successful_requests": len(ok),
        "failed_requests": fail,
        "success_rate": round(len(ok) / len(samples), 4) if samples else 0.0,
        "req_per_s": round(len(ok) / runtime_s, 3) if runtime_s > 0 else 0.0,
        "output_tok_per_s": round(tot_out / runtime_s, 3) if runtime_s > 0 else 0.0,
        "total_output_tokens": tot_out,
        "goodput": {
            "goals_ms": goals,
            "successful": good,
            "rate_per_s": round(good / runtime_s, 3) if good is not None and runtime_s > 0 else None,
            "fraction": round(good / len(ok), 4) if good is not None and ok else None,
        } if goals else None,
        "ttft_ms": _full_stats(ttft),
        "tpot_ms": _full_stats(tpot),
        "itl_ms": _full_stats(itl_flat),
        "latency_ms": _full_stats(lat),
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
    for bucket in ("ttft_ms", "tpot_ms", "itl_ms", "latency_ms"):
        out[bucket] = {}
        for stat in ("mean", "std", "median", "p25", "p50", "p75", "p90", "p95", "p99", "p999", "min", "max"):
            vals = [s[bucket][stat] for s in summaries if s.get(bucket) and s[bucket].get(stat) is not None]
            if not vals:
                continue
            q1, q3 = iqr_range(vals)
            out[bucket][stat] = {
                "median": round(median(vals), 2),
                "iqr_q1": round(q1, 2),
                "iqr_q3": round(q3, 2),
                "all": [round(v, 2) for v in vals],
            }
    # Goodput passthrough (median of fraction across runs)
    fr_vals = [s["goodput"]["fraction"] for s in summaries if s.get("goodput") and s["goodput"].get("fraction") is not None]
    if fr_vals:
        rate_vals = [s["goodput"]["rate_per_s"] for s in summaries if s.get("goodput") and s["goodput"].get("rate_per_s") is not None]
        out["goodput"] = {
            "fraction": {"median": round(median(fr_vals), 4), "all": fr_vals},
            "rate_per_s": {"median": round(median(rate_vals), 3), "all": rate_vals} if rate_vals else None,
            "goals_ms": summaries[0]["goodput"].get("goals_ms"),
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

    _print_human_summary(measured_summaries, aggregate, args)
    return 0


def _print_human_summary(measured: list[dict], aggregate: dict, args: argparse.Namespace) -> None:
    """vllm-bench-style summary: TTFT/TPOT/ITL/E2E with mean/p50/p99 + throughput + goodput."""
    def fmt(v):
        if v is None:
            return "  -  "
        if isinstance(v, float):
            return f"{v:8.2f}"
        return str(v)

    # Print per-run table when multi-run, single-run otherwise.
    if args.repeat_runs == 1:
        s = measured[0]
        runs_label = "single run"
    else:
        s = None
        runs_label = f"median over {aggregate.get('runs', '?')} runs (warmup={args.warmup_runs})"

    def get(s_dict, *path):
        # Reach into per-run summary OR aggregate (which has .median wrapping)
        cur = s_dict
        for k in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    print(f"\n=========== {runs_label} ===========")
    if s is not None:
        # Single-run: read directly from summary
        print(f"  successful: {s['successful_requests']}/{s['total_requests']}  "
              f"runtime: {s['runtime_s']:.2f}s")
        print(f"  request throughput   : {s['req_per_s']:.3f} req/s")
        print(f"  output throughput    : {s['output_tok_per_s']:.3f} tok/s")
        if s.get("goodput"):
            g = s["goodput"]
            print(f"  goodput              : {g.get('rate_per_s'):.3f} req/s  ({(g.get('fraction') or 0)*100:.1f}%)")
            print(f"    goals: {g.get('goals_ms')}")
        for label, key in [("TTFT", "ttft_ms"), ("TPOT", "tpot_ms"), ("ITL", "itl_ms"), ("E2E", "latency_ms")]:
            st = s.get(key) or {}
            print(f"  {label:<5} (ms)  mean={fmt(st.get('mean'))} std={fmt(st.get('std'))} "
                  f"median={fmt(st.get('median'))} p90={fmt(st.get('p90'))} "
                  f"p99={fmt(st.get('p99'))} max={fmt(st.get('max'))}")
    else:
        # Multi-run: read aggregate (each metric is {median, iqr_q1, iqr_q3, all})
        succ = (aggregate.get("success_rate") or {}).get("all", [])
        print(f"  success_rate per run : {succ}")
        rps = aggregate.get("req_per_s") or {}
        ots = aggregate.get("output_tok_per_s") or {}
        rt  = aggregate.get("runtime_s") or {}
        print(f"  request throughput   : median={fmt(rps.get('median'))} req/s  IQR={fmt(rps.get('iqr_q1'))}-{fmt(rps.get('iqr_q3'))}  all={rps.get('all')}")
        print(f"  output throughput    : median={fmt(ots.get('median'))} tok/s  all={ots.get('all')}")
        print(f"  runtime/run          : median={fmt(rt.get('median'))} s  all={rt.get('all')}")
        gd = aggregate.get("goodput") or {}
        if gd:
            fr = gd.get("fraction") or {}
            rt_g = gd.get("rate_per_s") or {}
            print(f"  goodput              : rate median={fmt(rt_g.get('median'))} req/s  fraction median={fr.get('median')}  goals={gd.get('goals_ms')}")
        for label, key in [("TTFT", "ttft_ms"), ("TPOT", "tpot_ms"), ("ITL", "itl_ms"), ("E2E", "latency_ms")]:
            agg_b = aggregate.get(key) or {}
            print(f"  {label:<5} (ms median-of-runs)  "
                  f"mean={fmt(get(agg_b, 'mean', 'median'))}  "
                  f"median={fmt(get(agg_b, 'median', 'median'))}  "
                  f"p90={fmt(get(agg_b, 'p90', 'median'))}  "
                  f"p99={fmt(get(agg_b, 'p99', 'median'))}  "
                  f"max={fmt(get(agg_b, 'max', 'median'))}")
    print("=================================================\n")


if __name__ == "__main__":
    raise SystemExit(main())
