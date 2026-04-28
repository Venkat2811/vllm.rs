#!/usr/bin/env python3
"""Multi-turn stress benchmark client for an OpenAI-compatible chat server.

Each "client" (worker) runs a session of N rounds. Each round appends a user
turn to the messages list, sends a streaming chat completion, captures the
response, and appends it to messages for the next round. Captures the
prefix-cache hit rate (cached_tokens / prompt_tokens) per round so we can
attribute prefix-cache effectiveness across rounds.

CLI shape (RFC 0037 §4):
  --url, --served-model-name, --prompts-file
  --num-clients (parallel sessions, closed-loop)
  --rounds (or --min-rounds + --max-rounds for uniform)
  --turn-input-tokens (chars approx, used for non-first turns)
  --turn-output-tokens (max_tokens per turn)
  --rate (open-loop session start rate; 0 = closed-loop)
  --distribution {poisson,fixed,uniform} (open-loop only)
  --output-file
  --request-timeout-sec
  --seed
  --no-stream (force non-streaming; cached_tokens still in usage block)

Reads `prompts-file` JSONL, expecting `{"prompt": "...", "input_tokens": N}`.
First turn = pull a prompt at random.
Subsequent turns = take a fresh prompt and truncate to --turn-input-tokens chars
(so the per-round growth is bounded; the conversation history accumulates).

Output JSON: {
    "config": {...},
    "aggregate": {
        "per_round": [
            {"round": 1, "n": K, "rps": ..., "ttft_ms": {p50/p95/p99},
             "cached_tokens": {sum, mean, min, max},
             "prompt_tokens": {sum, mean},
             "cache_hit_rate": {mean, p50, p99}, ...},
            {"round": 2, ...},
            ...
        ],
        "overall": {...}
    },
    "sessions": [
        {"client_id": 0, "rounds": [{round_idx, ttft_ms, ..., cached_tokens, prompt_tokens}, ...]},
        ...
    ]
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Multi-turn stress benchmark.")
    p.add_argument("--url", required=True, help="Base server URL, e.g. http://127.0.0.1:8000")
    p.add_argument("--served-model-name", required=True)
    p.add_argument("--prompts-file", required=True,
                   help="JSONL with {'prompt': str, 'input_tokens': int}")
    p.add_argument("--num-clients", type=int, default=4,
                   help="Concurrent session workers (closed-loop)")
    rounds = p.add_mutually_exclusive_group(required=True)
    rounds.add_argument("--rounds", type=int, help="Fixed rounds per session")
    rounds.add_argument("--min-rounds", type=int, help="Min rounds (uniform)")
    p.add_argument("--max-rounds", type=int, default=None,
                   help="Max rounds (uniform; required if --min-rounds set)")
    p.add_argument("--num-sessions", type=int, default=None,
                   help="Total sessions to run; default=num-clients (one each)")
    p.add_argument("--turn-input-tokens", type=int, default=200,
                   help="Approx chars to use from a fresh prompt for round>1 turns")
    p.add_argument("--turn-output-tokens", type=int, default=64,
                   help="max_tokens per turn")
    p.add_argument("--rate", type=float, default=0.0,
                   help="Open-loop session-start rate (sessions/s); 0 = closed-loop")
    p.add_argument("--distribution", choices=["poisson", "fixed", "uniform"],
                   default="poisson", help="Open-loop arrival distribution")
    p.add_argument("--request-timeout-sec", type=float, default=120.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-file", required=True)
    p.add_argument("--no-stream", action="store_true",
                   help="Disable streaming (cached_tokens still arrives in usage)")
    return p


def load_prompts(path: str) -> list[str]:
    out: list[str] = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            t = d.get("prompt") or d.get("text")
            if t:
                out.append(t)
    if not out:
        raise SystemExit(f"No prompts loaded from {path}")
    return out


async def run_one_turn(
    sess: aiohttp.ClientSession,
    *,
    url: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    timeout_seconds: float,
    stream: bool,
) -> dict:
    """Send a single turn, return per-turn record (ttft, latency, content,
    output_tokens, prompt_tokens, cached_tokens, success)."""
    rec: dict = {
        "ttft_ms": None,
        "latency_ms": None,
        "output_tokens": 0,
        "prompt_tokens": 0,
        "cached_tokens": 0,
        "content": "",
        "success": False,
        "error": None,
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": stream,
    }
    if stream:
        payload["stream_options"] = {"include_usage": True}
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    dispatch_t = time.perf_counter()
    content_chunks: list[str] = []
    try:
        async with sess.post(
            url.rstrip("/") + "/v1/chat/completions",
            json=payload,
            timeout=timeout,
        ) as resp:
            if resp.status != 200:
                rec["error"] = f"HTTP {resp.status}: {(await resp.text())[:200]}"
                rec["latency_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
                return rec
            if stream:
                async for raw in resp.content:
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    body = line[len("data:"):].strip()
                    if body == "[DONE]":
                        break
                    msg = json.loads(body)
                    # Usage block (final chunk): pull cached/prompt/completion
                    usage = msg.get("usage")
                    if usage:
                        rec["prompt_tokens"] = usage.get("prompt_tokens", 0)
                        rec["output_tokens"] = usage.get("completion_tokens", 0)
                        details = usage.get("prompt_tokens_details") or {}
                        rec["cached_tokens"] = details.get("cached_tokens", 0)
                        continue
                    choices = msg.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    c = delta.get("content")
                    if c:
                        if rec["ttft_ms"] is None:
                            rec["ttft_ms"] = round(
                                (time.perf_counter() - dispatch_t) * 1000.0, 3
                            )
                        content_chunks.append(c)
            else:
                msg = await resp.json()
                choices = msg.get("choices") or []
                if choices:
                    content_chunks.append(
                        choices[0].get("message", {}).get("content", "") or ""
                    )
                usage = msg.get("usage") or {}
                rec["prompt_tokens"] = usage.get("prompt_tokens", 0)
                rec["output_tokens"] = usage.get("completion_tokens", 0)
                details = usage.get("prompt_tokens_details") or {}
                rec["cached_tokens"] = details.get("cached_tokens", 0)
                rec["ttft_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
        rec["latency_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
        if rec["ttft_ms"] is None:
            rec["ttft_ms"] = rec["latency_ms"]
        rec["content"] = "".join(content_chunks)
        rec["success"] = True
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["latency_ms"] = round((time.perf_counter() - dispatch_t) * 1000.0, 3)
    return rec


async def run_one_session(
    client_id: int,
    *,
    sess: aiohttp.ClientSession,
    args: argparse.Namespace,
    rng: random.Random,
    prompts: list[str],
) -> dict:
    """Run a multi-turn session: pick rounds count, build messages, capture per-round metrics."""
    if args.rounds is not None:
        n_rounds = args.rounds
    else:
        n_rounds = rng.randint(args.min_rounds, args.max_rounds)
    messages: list[dict] = []
    rounds: list[dict] = []
    for round_idx in range(1, n_rounds + 1):
        if round_idx == 1:
            user_text = prompts[rng.randrange(len(prompts))]
        else:
            # Follow-up turn: fresh prompt, truncated by --turn-input-tokens chars (~tokens)
            base = prompts[rng.randrange(len(prompts))]
            cutoff_chars = args.turn_input_tokens * 4  # rough chars/token
            user_text = base[:cutoff_chars]
        messages.append({"role": "user", "content": user_text})
        rec = await run_one_turn(
            sess,
            url=args.url,
            model=args.served_model_name,
            messages=messages,
            max_tokens=args.turn_output_tokens,
            timeout_seconds=args.request_timeout_sec,
            stream=not args.no_stream,
        )
        rec["round"] = round_idx
        rounds.append(rec)
        if rec["success"] and rec["content"]:
            messages.append({"role": "assistant", "content": rec["content"]})
        else:
            # Stop session on failed turn (history would diverge)
            break
    return {"client_id": client_id, "n_rounds_planned": n_rounds, "rounds": rounds}


async def closed_loop(
    args: argparse.Namespace, prompts: list[str]
) -> tuple[list[dict], float]:
    bench_start = time.perf_counter()
    rng = random.Random(args.seed)
    n_sessions = args.num_sessions if args.num_sessions else args.num_clients
    sem = asyncio.Semaphore(args.num_clients)
    sessions: list[dict] = []

    async with aiohttp.ClientSession() as sess:
        async def capped(i: int) -> None:
            local_rng = random.Random(args.seed + i + 1)
            async with sem:
                s = await run_one_session(
                    i, sess=sess, args=args, rng=local_rng, prompts=prompts
                )
                sessions.append(s)
        await asyncio.gather(*(capped(i) for i in range(n_sessions)))
    return sessions, time.perf_counter() - bench_start


async def open_loop(
    args: argparse.Namespace, prompts: list[str]
) -> tuple[list[dict], float]:
    bench_start = time.perf_counter()
    rng = random.Random(args.seed)
    n_sessions = args.num_sessions if args.num_sessions else args.num_clients
    sessions: list[dict] = []
    sem = asyncio.Semaphore(args.num_clients)

    def next_delay() -> float:
        if args.rate <= 0:
            return 0.0
        if args.distribution == "fixed":
            return 1.0 / args.rate
        if args.distribution == "uniform":
            return rng.uniform(0.0, 2.0 / args.rate)
        # poisson
        return rng.expovariate(args.rate)

    async with aiohttp.ClientSession() as sess:
        tasks: list[asyncio.Task] = []
        for i in range(n_sessions):
            d = next_delay()
            if d > 0:
                await asyncio.sleep(d)

            async def fire(idx: int) -> None:
                local_rng = random.Random(args.seed + idx + 1)
                async with sem:
                    s = await run_one_session(
                        idx, sess=sess, args=args, rng=local_rng, prompts=prompts
                    )
                    sessions.append(s)
            tasks.append(asyncio.create_task(fire(i)))
        await asyncio.gather(*tasks)
    return sessions, time.perf_counter() - bench_start


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def aggregate(sessions: list[dict], elapsed_s: float) -> dict:
    """Compute per-round and overall aggregates."""
    by_round: dict[int, list[dict]] = {}
    for s in sessions:
        for r in s["rounds"]:
            by_round.setdefault(r["round"], []).append(r)

    per_round = []
    for round_idx in sorted(by_round.keys()):
        recs = by_round[round_idx]
        succ = [r for r in recs if r["success"]]
        ttft = [r["ttft_ms"] for r in succ if r["ttft_ms"] is not None]
        latency = [r["latency_ms"] for r in succ if r["latency_ms"] is not None]
        cached = [r["cached_tokens"] for r in succ]
        prompt_tokens = [r["prompt_tokens"] for r in succ]
        out_tokens = [r["output_tokens"] for r in succ]
        hit_rates = [
            (r["cached_tokens"] / r["prompt_tokens"]) if r["prompt_tokens"] else 0.0
            for r in succ
        ]
        per_round.append({
            "round": round_idx,
            "n_total": len(recs),
            "n_success": len(succ),
            "success_rate": (len(succ) / len(recs)) if recs else 0.0,
            "ttft_ms": {
                "p50": round(percentile(ttft, 0.50), 3),
                "p95": round(percentile(ttft, 0.95), 3),
                "p99": round(percentile(ttft, 0.99), 3),
                "mean": round(statistics.mean(ttft), 3) if ttft else 0.0,
            },
            "latency_ms": {
                "p50": round(percentile(latency, 0.50), 3),
                "p95": round(percentile(latency, 0.95), 3),
                "p99": round(percentile(latency, 0.99), 3),
                "mean": round(statistics.mean(latency), 3) if latency else 0.0,
            },
            "prompt_tokens": {
                "sum": sum(prompt_tokens),
                "mean": round(statistics.mean(prompt_tokens), 1) if prompt_tokens else 0.0,
                "min": min(prompt_tokens) if prompt_tokens else 0,
                "max": max(prompt_tokens) if prompt_tokens else 0,
            },
            "cached_tokens": {
                "sum": sum(cached),
                "mean": round(statistics.mean(cached), 1) if cached else 0.0,
                "min": min(cached) if cached else 0,
                "max": max(cached) if cached else 0,
            },
            "completion_tokens": {
                "sum": sum(out_tokens),
                "mean": round(statistics.mean(out_tokens), 1) if out_tokens else 0.0,
            },
            "cache_hit_rate": {
                "mean": round(statistics.mean(hit_rates), 4) if hit_rates else 0.0,
                "p50": round(percentile(hit_rates, 0.50), 4),
                "p99": round(percentile(hit_rates, 0.99), 4),
            },
        })

    all_succ = [r for s in sessions for r in s["rounds"] if r["success"]]
    total_turns = sum(len(s["rounds"]) for s in sessions)
    total_succ = len(all_succ)
    total_prompt = sum(r["prompt_tokens"] for r in all_succ)
    total_cached = sum(r["cached_tokens"] for r in all_succ)
    total_out = sum(r["output_tokens"] for r in all_succ)
    overall = {
        "n_sessions": len(sessions),
        "n_turns_total": total_turns,
        "n_turns_success": total_succ,
        "success_rate": (total_succ / total_turns) if total_turns else 0.0,
        "elapsed_s": round(elapsed_s, 3),
        "turns_per_s": round(total_succ / elapsed_s, 4) if elapsed_s > 0 else 0.0,
        "sessions_per_s": round(len(sessions) / elapsed_s, 4) if elapsed_s > 0 else 0.0,
        "total_prompt_tokens": total_prompt,
        "total_cached_tokens": total_cached,
        "total_completion_tokens": total_out,
        "overall_cache_hit_rate": round(total_cached / total_prompt, 4) if total_prompt else 0.0,
    }
    return {"per_round": per_round, "overall": overall}


async def main_async(args: argparse.Namespace) -> int:
    if args.min_rounds is not None and args.max_rounds is None:
        print("--min-rounds requires --max-rounds", file=sys.stderr)
        return 2
    prompts = load_prompts(args.prompts_file)
    print(f"loaded {len(prompts)} prompts", file=sys.stderr)
    if args.rate > 0:
        sessions, elapsed = await open_loop(args, prompts)
    else:
        sessions, elapsed = await closed_loop(args, prompts)

    agg = aggregate(sessions, elapsed)
    out = {
        "config": {
            "url": args.url,
            "served_model_name": args.served_model_name,
            "prompts_file": args.prompts_file,
            "num_clients": args.num_clients,
            "num_sessions": args.num_sessions or args.num_clients,
            "rounds": args.rounds,
            "min_rounds": args.min_rounds,
            "max_rounds": args.max_rounds,
            "turn_input_tokens": args.turn_input_tokens,
            "turn_output_tokens": args.turn_output_tokens,
            "rate": args.rate,
            "distribution": args.distribution,
            "stream": not args.no_stream,
            "seed": args.seed,
        },
        "aggregate": agg,
        "sessions": sessions,
    }
    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_file, "w") as f:
        json.dump(out, f, indent=2)

    o = agg["overall"]
    print(
        f"sessions={o['n_sessions']} turns_ok={o['n_turns_success']}/{o['n_turns_total']} "
        f"success={o['success_rate']*100:.0f}%  turns/s={o['turns_per_s']:.3f}  "
        f"hit_rate={o['overall_cache_hit_rate']*100:.1f}%  elapsed={elapsed:.1f}s",
        file=sys.stderr,
    )
    for r in agg["per_round"]:
        print(
            f"  round {r['round']:2d}: n={r['n_success']:3d}/{r['n_total']:3d}  "
            f"ttft p50={r['ttft_ms']['p50']:7.0f}ms  p99={r['ttft_ms']['p99']:7.0f}ms  "
            f"hit={r['cache_hit_rate']['mean']*100:5.1f}%  "
            f"prompt_tok mean={r['prompt_tokens']['mean']:6.0f}",
            file=sys.stderr,
        )
    return 0 if o["success_rate"] > 0 else 1


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
