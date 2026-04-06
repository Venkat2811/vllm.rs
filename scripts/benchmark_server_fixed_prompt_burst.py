#!/usr/bin/env python3
import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

import aiohttp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark fixed-prompt burst serving against an OpenAI-compatible chat server."
    )
    parser.add_argument("--url", required=True, help="Base server URL, e.g. http://127.0.0.1:18080")
    parser.add_argument("--served-model-name", required=True)
    parser.add_argument("--prompt-text", required=True)
    parser.add_argument("--num-requests", type=int, required=True)
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--max-tokens", type=int, default=1)
    parser.add_argument("--request-timeout-sec", type=float, default=300.0)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--no-stream", action="store_true")
    return parser


async def run_request(
    session: aiohttp.ClientSession,
    *,
    url: str,
    model: str,
    prompt_text: str,
    max_tokens: int,
    timeout_seconds: float,
    stream: bool,
) -> dict[str, float | int | bool | str | None]:
    start = time.perf_counter()
    ttft_ms: float | None = None
    output_chunks = 0
    output_text_parts: list[str] = []
    output_tokens = 0

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": max_tokens,
        "stream": stream,
    }

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with session.post(
        f"{url.rstrip('/')}/v1/chat/completions",
        json=payload,
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        if stream:
            async for raw_chunk in response.content:
                raw_line = raw_chunk.decode("utf-8", errors="replace").strip()
                if not raw_line or not raw_line.startswith("data:"):
                    continue
                payload_text = raw_line[len("data:") :].strip()
                if payload_text == "[DONE]":
                    break
                message = json.loads(payload_text)
                choices = message.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - start) * 1000.0
                    output_chunks += 1
                    output_text_parts.append(content)
                    output_tokens += 1
        else:
            message = await response.json()
            text = (
                message.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if text:
                output_text_parts.append(text)
                output_tokens = 1
            ttft_ms = (time.perf_counter() - start) * 1000.0

    latency_ms = (time.perf_counter() - start) * 1000.0
    if ttft_ms is None:
        ttft_ms = latency_ms

    return {
        "ttft_ms": round(ttft_ms, 3),
        "latency_ms": round(latency_ms, 3),
        "output_chunks": output_chunks,
        "output_tokens": output_tokens,
        "success": True,
        "output_text": "".join(output_text_parts),
    }


async def execute_burst(args: argparse.Namespace) -> list[dict[str, float | int | bool | str | None]]:
    semaphore = asyncio.Semaphore(args.concurrency)

    async with aiohttp.ClientSession() as session:
        async def one_request() -> dict[str, float | int | bool | str | None]:
            async with semaphore:
                return await run_request(
                    session,
                    url=args.url,
                    model=args.served_model_name,
                    prompt_text=args.prompt_text,
                    max_tokens=args.max_tokens,
                    timeout_seconds=args.request_timeout_sec,
                    stream=not args.no_stream,
                )

        tasks = [asyncio.create_task(one_request()) for _ in range(args.num_requests)]
        return await asyncio.gather(*tasks)


def summarize(samples: list[dict[str, float | int | bool | str | None]], runtime_sec: float) -> str:
    successes = [sample for sample in samples if sample.get("success")]
    if not successes:
        raise RuntimeError("no successful burst samples collected")

    ttft_values = [float(sample["ttft_ms"]) for sample in successes]
    latency_values = [float(sample["latency_ms"]) for sample in successes]

    def avg_min_max(name: str, values: list[float]) -> list[str]:
        return [
            f"[{name}] avg: {statistics.mean(values):.2f}, "
            f"min: {min(values):.2f}, max: {max(values):.2f}"
        ]

    lines = [
        "Collecting statistics...",
        f"runtime_sec = {runtime_sec:.3f}",
        f"requests_per_sec = {len(successes) / runtime_sec:.3f}",
        *avg_min_max("ttft_ms", ttft_values),
        "[tpot_ms] avg: 0.00, min: 0.00, max: 0.00",
        *avg_min_max("latency_ms", latency_values),
        f"successful_requests = {len(successes)}",
        f"first_completion_ms = {min(latency_values):.2f}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.num_requests <= 0:
        print("--num-requests must be > 0", file=sys.stderr)
        return 1
    if args.concurrency <= 0:
        print("--concurrency must be > 0", file=sys.stderr)
        return 1

    started_at = time.perf_counter()
    samples = asyncio.run(execute_burst(args))
    runtime_sec = time.perf_counter() - started_at

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")

    sys.stdout.write(summarize(samples, runtime_sec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
