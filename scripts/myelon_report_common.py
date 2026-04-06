#!/usr/bin/env python3
import csv
import json
import subprocess
from pathlib import Path


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _run_capture(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def get_repo_state(repo_root: Path) -> dict[str, object]:
    branch = _run_capture(["git", "branch", "--show-current"])
    commit = _run_capture(["git", "rev-parse", "HEAD"])
    status = _run_capture(["git", "status", "--short"])
    return {
        "repo_path": str(repo_root),
        "branch": branch.strip() if branch else None,
        "commit": commit.strip() if commit else None,
        "status": status.strip() if status else "",
    }


def capture_raw_system_info(output_root: Path) -> dict[str, str]:
    raw_dir = output_root / "raw" / "system_info"
    raw_dir.mkdir(parents=True, exist_ok=True)

    captures: list[tuple[str, list[str]]] = [
        ("hostnamectl.txt", ["hostnamectl"]),
        ("lscpu.txt", ["lscpu"]),
        ("free_h.txt", ["free", "-h"]),
        ("df_h.txt", ["df", "-h"]),
        ("uname.txt", ["uname", "-a"]),
        ("nvidia_smi.txt", ["nvidia-smi"]),
        ("nvidia_smi_topology.txt", ["nvidia-smi", "topo", "-m"]),
    ]

    paths: dict[str, str] = {}
    for filename, command in captures:
        output = _run_capture(command)
        if output is None:
            continue
        capture_path = raw_dir / filename
        capture_path.write_text(output, encoding="utf-8")
        paths[filename] = str(capture_path)
    return paths


def write_system_snapshot(
    output_root: Path,
    machine_profile: dict[str, object],
    repo_state: dict[str, object],
    raw_captures: dict[str, str],
) -> dict[str, str]:
    reports_dir = output_root / "reports" / "system_info"
    reports_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "machine_profile": machine_profile,
        "repo_state": repo_state,
        "raw_captures": raw_captures,
    }

    json_path = reports_dir / "system_snapshot.json"
    csv_path = reports_dir / "system_snapshot.csv"
    md_path = reports_dir / "system_snapshot.md"

    _write_json(json_path, snapshot)

    csv_rows = []
    for key, value in machine_profile.items():
        if key == "gpu_inventory":
            continue
        csv_rows.append({"section": "machine_profile", "key": key, "value": value})
    for key, value in repo_state.items():
        csv_rows.append({"section": "repo_state", "key": key, "value": value})
    _write_csv(csv_path, csv_rows, ["section", "key", "value"])

    lines = [
        "# System Snapshot",
        "",
        "## Key Facts",
        "",
        "| Key | Value |",
        "| --- | --- |",
    ]
    for key, value in machine_profile.items():
        if key == "gpu_inventory":
            continue
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Repo State",
            "",
            "| Key | Value |",
            "| --- | --- |",
        ]
    )
    for key, value in repo_state.items():
        lines.append(f"| {key} | {value} |")
    if raw_captures:
        lines.extend(
            [
                "",
                "## Raw Command Captures",
                "",
                "| Capture | Path |",
                "| --- | --- |",
            ]
        )
        for key, value in sorted(raw_captures.items()):
            lines.append(f"| {key} | {value} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "md": str(md_path),
    }


def build_case_rows(report: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in report.get("cases", []):
        summary = case.get("summary") if isinstance(case, dict) else None
        measured_summary = case.get("measured_summary") if isinstance(case, dict) else None
        row: dict[str, object] = {
            "label": case.get("label"),
            "execution_variant": case.get("execution_variant", case.get("label")),
            "stop_point": case.get("stop_point", "full_completion"),
            "skip_reason": case.get("skip_reason"),
            "benchmark_exit_code": case.get("benchmark_exit_code"),
        }
        if isinstance(summary, dict):
            table = summary.get("table", {})
            row["requests_per_sec"] = summary.get("requests_per_sec")
            row["runtime_sec"] = summary.get("runtime_sec")
            row["ttft_ms_mean"] = table.get("ttft_ms", {}).get("mean")
            row["tpot_ms_mean"] = table.get("tpot_ms", {}).get("mean")
            row["latency_ms_mean"] = table.get("latency_ms", {}).get("mean")
        if isinstance(measured_summary, dict):
            row["prompt_seconds_mean"] = measured_summary.get("prompt_seconds", {}).get("mean")
            row["prompt_tps_mean"] = measured_summary.get(
                "prompt_tokens_per_second", {}
            ).get("mean")
            row["decode_seconds_mean"] = measured_summary.get("decode_seconds", {}).get("mean")
            row["decode_tps_mean"] = measured_summary.get(
                "decode_tokens_per_second", {}
            ).get("mean")
        rows.append(row)
    return rows


def write_benchmark_reports(
    output_root: Path,
    report: dict[str, object],
    report_path: Path,
) -> dict[str, str]:
    reports_dir = output_root / "reports" / "benchmarks"
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary_md_path = reports_dir / "run_summary.md"
    case_csv_path = reports_dir / "run_details.csv"

    contract = report.get("benchmark_contract", {})
    case_rows = build_case_rows(report)
    fieldnames = sorted({key for row in case_rows for key in row.keys()}) if case_rows else [
        "label",
        "execution_variant",
        "stop_point",
        "skip_reason",
    ]
    _write_csv(case_csv_path, case_rows, fieldnames)

    lines = [
        "# Benchmark Summary",
        "",
        "| Key | Value |",
        "| --- | --- |",
        f"| benchmark_family | {contract.get('benchmark_family')} |",
        f"| benchmark_submode | {contract.get('benchmark_submode')} |",
        f"| workload_class | {contract.get('workload_class')} |",
        f"| topology_overlay | {contract.get('topology_overlay')} |",
        f"| transport_mode | {contract.get('transport_mode')} |",
        f"| run_class | {contract.get('run_class')} |",
        f"| stop_point | {contract.get('stop_point')} |",
        f"| report_json | {report_path} |",
        "",
        "## Case Summary",
        "",
    ]

    if case_rows:
        header = fieldnames
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in case_rows:
            lines.append("| " + " | ".join(str(row.get(name, "")) for name in header) + " |")
    else:
        lines.append("No case rows were available.")

    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "summary_md": str(summary_md_path),
        "details_csv": str(case_csv_path),
    }


def write_report_bundle(
    output_root: Path,
    report: dict[str, object],
    report_path: Path,
    repo_root: Path,
    capture_raw_system: bool = True,
) -> dict[str, object]:
    repo_state = get_repo_state(repo_root)
    raw_captures = capture_raw_system_info(output_root) if capture_raw_system else {}
    system_info = write_system_snapshot(
        output_root=output_root,
        machine_profile=report.get("machine_profile", {}),
        repo_state=repo_state,
        raw_captures=raw_captures,
    )
    benchmarks = write_benchmark_reports(
        output_root=output_root,
        report=report,
        report_path=report_path,
    )
    return {
        "system_info": system_info,
        "benchmarks": benchmarks,
        "repo_state": repo_state,
        "raw_captures": raw_captures,
    }
