#!/usr/bin/env python3
import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


LINE_RE = re.compile(r"\[MyelonInstr\]\s+(\{.*\})")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate [MyelonInstr] JSON lines from logs.")
    p.add_argument("--log", action="append", required=True, help="Log file to scan. Repeatable.")
    p.add_argument("--output-json", required=True)
    p.add_argument("--output-txt", required=True)
    return p.parse_args()


def load_events(paths: list[str]) -> list[dict]:
    events: list[dict] = []
    for path in paths:
        for line in Path(path).read_text(errors="replace").splitlines():
            m = LINE_RE.search(line)
            if not m:
                continue
            try:
                event = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
            event["_source_log"] = path
            events.append(event)
    return events


def ns_stats(values: list[int]) -> dict:
    if not values:
        return {"count": 0}
    vals = sorted(values)
    return {
        "count": len(vals),
        "sum_ns": int(sum(vals)),
        "mean_ns": int(statistics.mean(vals)),
        "p50_ns": int(vals[len(vals) // 2]),
        "p95_ns": int(vals[min(len(vals) - 1, int(len(vals) * 0.95))]),
        "max_ns": int(vals[-1]),
    }


def us_stats(values: list[int]) -> dict:
    if not values:
        return {"count": 0}
    vals = sorted(values)
    return {
        "count": len(vals),
        "sum_us": int(sum(vals)),
        "mean_us": float(statistics.mean(vals)),
        "p50_us": vals[len(vals) // 2],
        "p95_us": vals[min(len(vals) - 1, int(len(vals) * 0.95))],
        "max_us": vals[-1],
    }


def summarize(events: list[dict]) -> dict:
    out: dict = {"total_events": len(events), "scopes": {}}

    ipc_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    pd_comm_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    pd_kv_groups: dict[str, list[dict]] = defaultdict(list)

    for event in events:
        scope = event.get("scope")
        if scope == "ipc":
            ipc_groups[(event.get("request_kind", "unknown"), event.get("status", "unknown"))].append(
                event
            )
        elif scope == "pd_comm":
            pd_comm_groups[
                (event.get("direction", "unknown"), event.get("role", "unknown"), event.get("message", "unknown"))
            ].append(event)
        elif scope == "pd_kv":
            pd_kv_groups[event.get("op", "unknown")].append(event)

    ipc_summary = {}
    for key, group in sorted(ipc_groups.items()):
        kind, status = key
        ipc_summary[f"{kind}:{status}"] = {
            "count": len(group),
            "payload_bytes": us_stats([int(e.get("payload_bytes", 0)) for e in group]),
            "response_payload_bytes": us_stats([int(e.get("response_payload_bytes", 0)) for e in group]),
            "response_count": us_stats([int(e.get("response_count", 0)) for e in group]),
            "encode_ns": ns_stats([int(e.get("encode_ns", 0)) for e in group]),
            "publish_ns": ns_stats([int(e.get("publish_ns", 0)) for e in group]),
            "collect_ns": ns_stats([int(e.get("collect_ns", 0)) for e in group]),
            "decode_ns": ns_stats([int(e.get("decode_ns", 0)) for e in group]),
        }
    out["scopes"]["ipc"] = ipc_summary

    pd_comm_summary = {}
    for key, group in sorted(pd_comm_groups.items()):
        direction, role, message = key
        pd_comm_summary[f"{direction}:{role}:{message}"] = {
            "count": len(group),
            "payload_bytes": us_stats([int(e.get("payload_bytes", 0)) for e in group]),
            "serialize_ns": ns_stats([int(e.get("serialize_ns", 0)) for e in group]),
            "io_ns": ns_stats([int(e.get("io_ns", 0)) for e in group]),
            "decode_ns": ns_stats([int(e.get("decode_ns", 0)) for e in group]),
        }
    out["scopes"]["pd_comm"] = pd_comm_summary

    pd_kv_summary = {}
    for op, group in sorted(pd_kv_groups.items()):
        metrics = {}
        for field in ("gpu_to_cpu_us", "cpu_to_gpu_us", "total_us", "layers", "blocks"):
            vals = [int(e[field]) for e in group if field in e]
            if vals:
                metrics[field] = us_stats(vals)
        metrics["count"] = len(group)
        pd_kv_summary[op] = metrics
    out["scopes"]["pd_kv"] = pd_kv_summary
    return out


def render_text(summary: dict) -> str:
    lines: list[str] = []
    lines.append("Myelon instrumentation aggregate")
    lines.append("================================")
    lines.append(f"total_events={summary['total_events']}")
    lines.append("")

    lines.append("IPC")
    lines.append("---")
    for key, item in summary["scopes"]["ipc"].items():
        lines.append(
            f"{key}: count={item['count']} "
            f"payload_mean={item['payload_bytes'].get('mean_us', 0):.1f}B "
            f"encode_mean_ns={item['encode_ns'].get('mean_ns', 0)} "
            f"publish_mean_ns={item['publish_ns'].get('mean_ns', 0)} "
            f"collect_mean_ns={item['collect_ns'].get('mean_ns', 0)} "
            f"decode_mean_ns={item['decode_ns'].get('mean_ns', 0)}"
        )
    lines.append("")

    lines.append("PD comm")
    lines.append("-------")
    for key, item in summary["scopes"]["pd_comm"].items():
        lines.append(
            f"{key}: count={item['count']} "
            f"payload_mean={item['payload_bytes'].get('mean_us', 0):.1f}B "
            f"serialize_mean_ns={item['serialize_ns'].get('mean_ns', 0)} "
            f"io_mean_ns={item['io_ns'].get('mean_ns', 0)} "
            f"decode_mean_ns={item['decode_ns'].get('mean_ns', 0)}"
        )
    lines.append("")

    lines.append("PD kv")
    lines.append("-----")
    for key, item in summary["scopes"]["pd_kv"].items():
        bits = [f"{key}: count={item['count']}"]
        for field in ("gpu_to_cpu_us", "cpu_to_gpu_us", "total_us", "layers", "blocks"):
            if field in item:
                bits.append(f"{field}_mean={item[field]['mean_us']:.1f}")
        lines.append(" ".join(bits))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    events = load_events(args.log)
    summary = summarize(events)
    Path(args.output_json).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.output_txt).write_text(render_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
