#!/usr/bin/env python3
"""Aggregate PD latency sweep cells into a side-by-side comparison.

Reads $ARTIFACT_ROOT/{myelon_2mb,tcp_loopback}/{closed_cN.json,open_rN.json}
and emits a Markdown table per (mode, param) point with TTFT and end-to-end
latency p50/p95/p99 across the two transports plus throughput.
"""
import json
import sys
from pathlib import Path


VARIANTS = ["myelon_2mb", "tcp_loopback"]


def load_cell(root: Path, variant: str, mode: str, param) -> dict | None:
    name = f"closed_c{param}.json" if mode == "closed" else f"open_r{param}.json"
    path = root / variant / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def median_of(d: dict, bucket: str, stat: str) -> float | None:
    agg = (d or {}).get("aggregate") or {}
    inner = (agg.get(bucket) or {}).get(stat) or {}
    return inner.get("median") if isinstance(inner, dict) else inner


def scalar_median(d: dict, key: str):
    agg = (d or {}).get("aggregate") or {}
    inner = agg.get(key)
    return inner.get("median") if isinstance(inner, dict) else inner


def fmt(x):
    if x is None:
        return "  -  "
    if isinstance(x, float):
        return f"{x:7.1f}"
    return str(x)


def pct_delta(a, b):
    if a is None or b is None or a == 0:
        return None
    return 100.0 * (b - a) / a


def emit_table(cells: dict, mode: str, params: list, bucket: str) -> str:
    rows = []
    rows.append(f"### {bucket} median (ms) — {mode} sweep")
    rows.append("")
    rows.append(f"| {'param':>5} | {'p50 myelon':>11} | {'p50 tcp':>10} | {'Δ%':>5} | {'p99 myelon':>11} | {'p99 tcp':>10} | {'Δ%':>5} |")
    rows.append("|---|---|---|---|---|---|---|")
    for p in params:
        m = cells["myelon_2mb"].get(p)
        t = cells["tcp_loopback"].get(p)
        m50 = median_of(m, bucket, "p50")
        t50 = median_of(t, bucket, "p50")
        m99 = median_of(m, bucket, "p99")
        t99 = median_of(t, bucket, "p99")
        d50 = pct_delta(t50, m50)
        d99 = pct_delta(t99, m99)
        rows.append(
            f"| {p:>5} | {fmt(m50):>11} | {fmt(t50):>10} | {fmt(d50):>5} | "
            f"{fmt(m99):>11} | {fmt(t99):>10} | {fmt(d99):>5} |"
        )
    return "\n".join(rows)


def emit_throughput_table(cells: dict, mode: str, params: list) -> str:
    rows = []
    rows.append(f"### Throughput — {mode} sweep")
    rows.append("")
    rows.append(f"| {'param':>5} | {'myelon req/s':>13} | {'tcp req/s':>10} | {'myelon tok/s':>13} | {'tcp tok/s':>10} |")
    rows.append("|---|---|---|---|---|")
    for p in params:
        m = cells["myelon_2mb"].get(p) or {}
        t = cells["tcp_loopback"].get(p) or {}
        rows.append(
            f"| {p:>5} | {fmt(scalar_median(m,'req_per_s')):>13} "
            f"| {fmt(scalar_median(t,'req_per_s')):>10} "
            f"| {fmt(scalar_median(m,'output_tok_per_s')):>13} "
            f"| {fmt(scalar_median(t,'output_tok_per_s')):>10} |"
        )
    return "\n".join(rows)


def main():
    root = Path(sys.argv[1])
    concurrency_list = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1 4 16 64 128 256").split()]
    rps_list = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "2 5 10 20 40").split()]

    closed = {v: {c: load_cell(root, v, "closed", c) for c in concurrency_list} for v in VARIANTS}
    open_  = {v: {r: load_cell(root, v, "open",   r) for r in rps_list} for v in VARIANTS}

    md = []
    md.append("# PD latency sweep — Myelon-2MB vs TCP loopback")
    md.append("")
    md.append("Workload: PD tp2/tp2 Qwen3-0.6B (server GPUs 0,1; client 2,3), ShareGPT 1040±200-token prompts, max-tokens=64. Each cell: 1 warmup discarded + 2 measured runs of 20s, median+IQR.")
    md.append("")
    md.append(emit_table(closed, "closed-loop concurrency", concurrency_list, "ttft_ms"))
    md.append("")
    md.append(emit_table(closed, "closed-loop concurrency", concurrency_list, "latency_ms"))
    md.append("")
    md.append(emit_throughput_table(closed, "closed-loop concurrency", concurrency_list))
    md.append("")
    md.append(emit_table(open_, "open-loop RPS", rps_list, "ttft_ms"))
    md.append("")
    md.append(emit_table(open_, "open-loop RPS", rps_list, "latency_ms"))
    md.append("")
    md.append(emit_throughput_table(open_, "open-loop RPS", rps_list))
    md.append("")
    print("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
