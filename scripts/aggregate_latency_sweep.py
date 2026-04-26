#!/usr/bin/env python3
"""Aggregate latency sweep cells into a side-by-side comparison.

Reads $ARTIFACT_ROOT/{socket,myelon_owned,myelon_typed}/{closed_cN.json,open_rN.json}
and emits a Markdown table per (mode, param) point with TTFT and end-to-end
latency p50/p95/p99 across the three transports. Highlights any point where
Myelon and socket differ by more than the 3% noise floor we observed in the
throughput matrix.
"""
import json
import sys
from pathlib import Path


VARIANTS = ["socket", "myelon_owned", "myelon_typed"]


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
    header = f"| {'param':>5} | {'p50 socket':>10} | {'p50 owned':>9} | {'Δ%':>5} | {'p50 typed':>9} | {'Δ%':>5} | {'p99 socket':>10} | {'p99 owned':>9} | {'Δ%':>5} | {'p99 typed':>9} | {'Δ%':>5} |"
    sep = "|" + "|".join(["---"] * (header.count("|") - 1)) + "|"
    rows.append(header)
    rows.append(sep)
    for p in params:
        s_p50 = median_of(cells["socket"].get(p), bucket, "p50")
        o_p50 = median_of(cells["myelon_owned"].get(p), bucket, "p50")
        t_p50 = median_of(cells["myelon_typed"].get(p), bucket, "p50")
        s_p99 = median_of(cells["socket"].get(p), bucket, "p99")
        o_p99 = median_of(cells["myelon_owned"].get(p), bucket, "p99")
        t_p99 = median_of(cells["myelon_typed"].get(p), bucket, "p99")
        d_o50 = pct_delta(s_p50, o_p50)
        d_t50 = pct_delta(s_p50, t_p50)
        d_o99 = pct_delta(s_p99, o_p99)
        d_t99 = pct_delta(s_p99, t_p99)
        rows.append(
            f"| {p:>5} | {fmt(s_p50):>10} | {fmt(o_p50):>9} | {fmt(d_o50):>5} | "
            f"{fmt(t_p50):>9} | {fmt(d_t50):>5} | {fmt(s_p99):>10} | {fmt(o_p99):>9} | "
            f"{fmt(d_o99):>5} | {fmt(t_p99):>9} | {fmt(d_t99):>5} |"
        )
    return "\n".join(rows)


def scalar_median(d: dict, key: str) -> float | None:
    agg = (d or {}).get("aggregate") or {}
    inner = agg.get(key)
    if isinstance(inner, dict):
        return inner.get("median")
    return inner


def emit_throughput_table(cells: dict, mode: str, params: list) -> str:
    rows = []
    rows.append(f"### Throughput (req/s, output tok/s) — {mode} sweep")
    rows.append("")
    rows.append(f"| {'param':>5} | {'socket req/s':>12} | {'owned req/s':>12} | {'typed req/s':>12} | {'socket tok/s':>12} | {'owned tok/s':>12} | {'typed tok/s':>12} |")
    rows.append("|---|---|---|---|---|---|---|")
    for p in params:
        s = cells["socket"].get(p) or {}
        o = cells["myelon_owned"].get(p) or {}
        t = cells["myelon_typed"].get(p) or {}
        rows.append(
            f"| {p:>5} | {fmt(scalar_median(s,'req_per_s')):>12} "
            f"| {fmt(scalar_median(o,'req_per_s')):>12} "
            f"| {fmt(scalar_median(t,'req_per_s')):>12} "
            f"| {fmt(scalar_median(s,'output_tok_per_s')):>12} "
            f"| {fmt(scalar_median(o,'output_tok_per_s')):>12} "
            f"| {fmt(scalar_median(t,'output_tok_per_s')):>12} |"
        )
    return "\n".join(rows)


def main():
    root = Path(sys.argv[1])
    concurrency_list = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1 4 16 64 128 256").split()]
    rps_list = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "2 5 10 20 40").split()]

    closed = {v: {c: load_cell(root, v, "closed", c) for c in concurrency_list} for v in VARIANTS}
    open_  = {v: {r: load_cell(root, v, "open",   r) for r in rps_list} for v in VARIANTS}

    md = []
    md.append("# Latency sweep — socket vs myelon (owned, typed)")
    md.append("")
    md.append("Workload: Qwen3-0.6B tp4 single HTTP server, ShareGPT 1040±200-token prompts, max-tokens=64. Each cell: 1 warmup discarded + 2 measured runs of 20s, median+IQR.")
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
