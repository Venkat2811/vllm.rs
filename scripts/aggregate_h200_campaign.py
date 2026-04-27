#!/usr/bin/env python3
"""Aggregate H200 campaign cells into Markdown comparison tables.

Reads $ART/<phase>/<cell>/<bucket>/closed_c<C>.json and produces:
  - Per-(topo, bucket) socket-vs-myelon side-by-side
  - Best Δ% per concurrency point
  - Goodput compliance per cell

Usage:
  python aggregate_h200_campaign.py [--art DIR] [--phases p1 p2 p3 ...]
"""
import argparse
import json
import os
import re
import sys
from glob import glob
from pathlib import Path


PHASES = ["phase1_socket", "phase2_myelon_ipc", "phase3_myelon_kv", "phase4_myelon_both"]


def load_cell(path: str) -> dict | None:
    try:
        return json.load(open(path))
    except Exception:
        return None


def cell_summary(cell: dict | None) -> dict:
    if not cell:
        return {}
    a = cell.get("aggregate", {}) or {}
    out = {}
    for k in ("req_per_s", "output_tok_per_s", "success_rate", "runtime_s"):
        v = a.get(k)
        out[k] = v.get("median") if isinstance(v, dict) else v
    for bucket in ("ttft_ms", "tpot_ms", "itl_ms", "latency_ms"):
        b = a.get(bucket) or {}
        for stat in ("median", "p90", "p99"):
            sd = b.get(stat) or {}
            out[f"{bucket}_{stat}"] = sd.get("median") if isinstance(sd, dict) else sd
    g = a.get("goodput")
    if g:
        out["goodput_rate"] = (g.get("rate_per_s") or {}).get("median")
        out["goodput_frac"] = (g.get("fraction") or {}).get("median")
    return out


def list_cells(art: Path, phase: str, cell: str, bucket: str) -> list[tuple[int, str]]:
    pat = art / phase / cell / bucket / "closed_c*.json"
    items = []
    for p in sorted(glob(str(pat))):
        m = re.search(r"closed_c(\d+)\.json$", p)
        if m:
            items.append((int(m.group(1)), p))
    return sorted(items)


def fmt(v):
    if v is None:
        return "  -  "
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def pct(a, b):
    if a is None or b is None or a == 0:
        return None
    return 100.0 * (b - a) / a


def emit_pair_table(art: Path, sock_phase: str, sock_cell: str, mye_phase: str, mye_cell: str, bucket: str) -> str:
    """Side-by-side table for one (topo, bucket) pair across two phases."""
    sock = {c: cell_summary(load_cell(p)) for c, p in list_cells(art, sock_phase, sock_cell, bucket)}
    mye  = {c: cell_summary(load_cell(p)) for c, p in list_cells(art, mye_phase,  mye_cell,  bucket)}
    cs = sorted(set(sock) | set(mye))
    if not cs:
        return f"_(no cells found for {sock_cell}/{bucket} vs {mye_cell}/{bucket})_"

    lines = [f"### {sock_cell} ({sock_phase}) vs {mye_cell} ({mye_phase}) — bucket={bucket}", ""]
    h = (f"|   C | sock RPS | mye RPS  | Δ RPS%  | sock TTFT p50 | mye TTFT p50 | Δ TTFT% | "
         f"sock TTFT p99 | mye TTFT p99 | sock E2E p50 | mye E2E p50 | sock SR | mye SR |")
    sep = "|----:" + "|".join(["------"] * (h.count("|") - 2)) + "|"
    lines.append(h)
    lines.append("|" + "|".join(["---"] * (h.count("|") - 1)) + "|")
    best_d = None
    for c in cs:
        s = sock.get(c, {})
        m = mye.get(c, {})
        d_rps = pct(s.get("req_per_s"), m.get("req_per_s"))
        d_ttft = pct(s.get("ttft_ms_median"), m.get("ttft_ms_median"))
        if d_rps is not None and (best_d is None or d_rps > best_d):
            best_d = d_rps
        lines.append(
            f"| {c:>3} | {fmt(s.get('req_per_s'))} | {fmt(m.get('req_per_s'))} | "
            f"{fmt(d_rps)} | {fmt(s.get('ttft_ms_median'))} | {fmt(m.get('ttft_ms_median'))} | "
            f"{fmt(d_ttft)} | {fmt(s.get('ttft_ms_p99'))} | {fmt(m.get('ttft_ms_p99'))} | "
            f"{fmt(s.get('latency_ms_median'))} | {fmt(m.get('latency_ms_median'))} | "
            f"{fmt(s.get('success_rate'))} | {fmt(m.get('success_rate'))} |"
        )
    lines.append("")
    if best_d is not None:
        lines.append(f"**Best Myelon Δ RPS**: {best_d:+.2f}%")
    lines.append("")
    return "\n".join(lines)


def emit_phase_summary(art: Path, phase: str) -> str:
    """One-row-per-cell summary for a phase."""
    pdir = art / phase
    if not pdir.is_dir():
        return ""
    rows = []
    for cell_dir in sorted(pdir.iterdir()):
        if not cell_dir.is_dir():
            continue
        for bucket_dir in sorted(cell_dir.iterdir()):
            if not bucket_dir.is_dir():
                continue
            cells = sorted(glob(str(bucket_dir / "closed_c*.json")))
            best_rps = 0.0
            best_C = None
            for cp in cells:
                m = re.search(r"closed_c(\d+)\.json$", cp)
                C = int(m.group(1)) if m else None
                s = cell_summary(load_cell(cp))
                rps = s.get("req_per_s") or 0
                if rps > best_rps:
                    best_rps = rps
                    best_C = C
            rows.append((cell_dir.name, bucket_dir.name, best_C, best_rps, len(cells)))
    if not rows:
        return ""
    out = [f"### {phase}", "", "| Cell | Bucket | Cells | Best C | Best req/s |", "|---|---|---:|---:|---:|"]
    for cell, bucket, bC, brps, nc in rows:
        out.append(f"| {cell} | {bucket} | {nc} | {bC if bC is not None else '-'} | {brps:.2f} |")
    out.append("")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--art", default="/root/Documents/myelon-launch/ai-chat-exports/.0_agentic_engineering/3_vllm_rs/0_myelon_integ/2_artifacts/2026-04-27_h200_myelon_campaign")
    p.add_argument("--out", default=None, help="output md path (default: ART/CAMPAIGN_REPORT.md)")
    args = p.parse_args()
    art = Path(args.art)
    out_path = Path(args.out) if args.out else art / "CAMPAIGN_REPORT.md"

    md = ["# H200 Myelon Campaign — Aggregated Results", ""]
    md.append(f"Source: `{art}`")
    md.append("")

    # Per-phase summaries
    md.append("## Per-phase quick view")
    md.append("")
    for ph in PHASES:
        s = emit_phase_summary(art, ph)
        if s:
            md.append(s)

    # Day 1 critical pair: S-tp2 vs M-tp2 / 1k
    md.append("## Day 1 decision gate")
    md.append("")
    md.append(emit_pair_table(art, "phase1_socket", "S-tp2", "phase2_myelon_ipc", "M-tp2", "1k"))

    # Other comparisons (both must exist to render)
    md.append("## Phase 1 vs Phase 2 — other topologies / buckets")
    md.append("")
    for sock_cell, mye_cell in [("S-tp4", "M-tp4"), ("S-pd1", "M-pd1"), ("S-pd2", "M-pd2")]:
        for bucket in ("1k", "2k"):
            md.append(emit_pair_table(art, "phase1_socket", sock_cell, "phase2_myelon_ipc", mye_cell, bucket))

    # PD KV path comparison: socket-PD baseline vs Myelon-KV
    md.append("## Phase 1 vs Phase 3 — PD KV transport (socket vs Myelon SHM)")
    md.append("")
    for cell in ("pd1", "pd2"):
        md.append(emit_pair_table(art, "phase1_socket", f"S-{cell}", "phase3_myelon_kv", f"K-{cell}", "1k"))

    # Phase 4 (both Myelon) vs Phase 1 baseline
    md.append("## Phase 1 vs Phase 4 — Myelon both (IPC + KV)")
    md.append("")
    for cell_pair in [("S-tp2", "B-tp2"), ("S-pd2", "B-pd2")]:
        md.append(emit_pair_table(art, "phase1_socket", cell_pair[0], "phase4_myelon_both", cell_pair[1], "1k"))

    out_path.write_text("\n".join(md))
    print(f"wrote {out_path}", file=sys.stderr)
    print(f"size: {out_path.stat().st_size} bytes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
