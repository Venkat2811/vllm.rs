#!/usr/bin/env python3
"""Aggregate stress benchmark results from multiple JSON files into a comparison table."""
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict


def cell_label(filename: str) -> str:
    name = Path(filename).stem
    return name


def load_summary(path: Path) -> dict:
    d = json.load(open(path))
    s = d["summary"]
    cfg = d["config"]
    return {
        "label": cell_label(str(path)),
        "concurrency": cfg.get("concurrency"),
        "request_rate": cfg.get("request_rate"),
        "num_requests": cfg.get("num_requests"),
        "req_per_s": s["req_per_s"],
        "out_tok_per_s": s["output_tok_per_s"],
        "success": s["successful_requests"],
        "total": s["total_requests"],
        "ttft_p50": s["ttft_ms"]["p50"],
        "ttft_p95": s["ttft_ms"]["p95"],
        "ttft_p99": s["ttft_ms"]["p99"],
        "ttft_max": s["ttft_ms"]["max"],
        "lat_p50": s["latency_ms"]["p50"],
        "lat_p95": s["latency_ms"]["p95"],
        "lat_p99": s["latency_ms"]["p99"],
        "lat_max": s["latency_ms"]["max"],
        "runtime_s": s["runtime_s"],
    }


def fmt_table(rows: list[dict], cols: list[tuple[str, str]]) -> str:
    headers = [c[1] for c in cols]
    table = [headers]
    for r in rows:
        table.append([str(r.get(c[0], "")) for c in cols])
    widths = [max(len(row[i]) for row in table) for i in range(len(headers))]
    out = []
    for i, row in enumerate(table):
        out.append("  ".join(c.rjust(widths[j]) for j, c in enumerate(row)))
        if i == 0:
            out.append("  ".join("-" * widths[j] for j in range(len(headers))))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--myelon-dir", required=True)
    ap.add_argument("--socket-dir", required=True)
    args = ap.parse_args()

    myelon = sorted([load_summary(p) for p in Path(args.myelon_dir).glob("*.json")], key=lambda r: r["label"])
    socket = sorted([load_summary(p) for p in Path(args.socket_dir).glob("*.json")], key=lambda r: r["label"])

    cols = [
        ("label", "cell"),
        ("req_per_s", "req/s"),
        ("out_tok_per_s", "out_tok/s"),
        ("success", "ok"),
        ("ttft_p50", "ttft50"),
        ("ttft_p95", "ttft95"),
        ("ttft_p99", "ttft99"),
        ("lat_p50", "lat50"),
        ("lat_p95", "lat95"),
        ("lat_p99", "lat99"),
        ("runtime_s", "wall_s"),
    ]
    print("# Myelon")
    print(fmt_table(myelon, cols))
    print()
    print("# Socket")
    print(fmt_table(socket, cols))
    print()

    # Pair by label
    by_label_m = {r["label"]: r for r in myelon}
    by_label_s = {r["label"]: r for r in socket}
    common = sorted(set(by_label_m) & set(by_label_s))
    print("# Δ Myelon vs Socket (pct)")
    diff_rows = []
    for lbl in common:
        m, s = by_label_m[lbl], by_label_s[lbl]
        def pct(a, b):
            if b in (None, 0) or a is None:
                return None
            return round((a - b) / b * 100.0, 1)
        diff_rows.append({
            "label": lbl,
            "Δreq/s_pct": pct(m["req_per_s"], s["req_per_s"]),
            "Δout_tok/s_pct": pct(m["out_tok_per_s"], s["out_tok_per_s"]),
            "Δttft50_pct": pct(m["ttft_p50"], s["ttft_p50"]),
            "Δttft95_pct": pct(m["ttft_p95"], s["ttft_p95"]),
            "Δttft99_pct": pct(m["ttft_p99"], s["ttft_p99"]),
            "Δlat50_pct": pct(m["lat_p50"], s["lat_p50"]),
            "Δlat95_pct": pct(m["lat_p95"], s["lat_p95"]),
            "Δlat99_pct": pct(m["lat_p99"], s["lat_p99"]),
        })
    diff_cols = [
        ("label", "cell"),
        ("Δreq/s_pct", "Δrps%"),
        ("Δout_tok/s_pct", "Δot/s%"),
        ("Δttft50_pct", "Δttft50%"),
        ("Δttft95_pct", "Δttft95%"),
        ("Δttft99_pct", "Δttft99%"),
        ("Δlat50_pct", "Δlat50%"),
        ("Δlat95_pct", "Δlat95%"),
        ("Δlat99_pct", "Δlat99%"),
    ]
    print(fmt_table(diff_rows, diff_cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
