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
        if case.get("skip_reason"):
            case_status = "skipped"
        elif case.get("stop_point") not in (None, "full_completion"):
            case_status = str(case.get("stop_point"))
        elif case.get("benchmark_exit_code") not in (None, 0):
            case_status = "benchmark_failed"
        else:
            case_status = "completed"
        row: dict[str, object] = {
            "label": case.get("label"),
            "execution_variant": case.get("execution_variant", case.get("label")),
            "case_status": case_status,
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


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_run_index_rows(report: dict[str, object], report_path: Path) -> list[dict[str, object]]:
    contract = report.get("benchmark_contract", {})
    machine_profile = report.get("machine_profile", {})
    model_capability = report.get("model_capability", {})
    gpu_inventory = machine_profile.get("gpu_inventory", [])
    gpu_names = []
    if isinstance(gpu_inventory, list):
        gpu_names = [item.get("name") for item in gpu_inventory if isinstance(item, dict)]

    return [
        {
            "benchmark_family": contract.get("benchmark_family"),
            "benchmark_submode": contract.get("benchmark_submode"),
            "workload_class": contract.get("workload_class"),
            "topology_overlay": contract.get("topology_overlay"),
            "transport_mode": contract.get("transport_mode"),
            "run_class": contract.get("run_class"),
            "status": report.get("status"),
            "stop_point": contract.get("stop_point"),
            "skip_reason": contract.get("skip_reason"),
            "host": machine_profile.get("hostname"),
            "gpu_names": ",".join(str(item) for item in gpu_names if item),
            "model_architecture": model_capability.get("architecture"),
            "pd_supported": model_capability.get("pd_supported"),
            "report_json": str(report_path),
        }
    ]


def build_side_by_side_rows(report: dict[str, object]) -> list[dict[str, object]]:
    case_rows = build_case_rows(report)
    baseline_case = next(
        (
            row
            for row in case_rows
            if "myelon" not in str(row.get("execution_variant", "")).lower()
        ),
        None,
    )
    myelon_case = next(
        (
            row
            for row in case_rows
            if "myelon" in str(row.get("execution_variant", "")).lower()
        ),
        None,
    )
    if not baseline_case or not myelon_case:
        return []

    rows: list[dict[str, object]] = []
    metrics = [
        "requests_per_sec",
        "runtime_sec",
        "ttft_ms_mean",
        "tpot_ms_mean",
        "latency_ms_mean",
        "prompt_seconds_mean",
        "prompt_tps_mean",
        "decode_seconds_mean",
        "decode_tps_mean",
    ]
    for metric in metrics:
        baseline_value = _to_float(baseline_case.get(metric))
        myelon_value = _to_float(myelon_case.get(metric))
        delta_percent = None
        if baseline_value not in (None, 0.0) and myelon_value is not None:
            delta_percent = ((myelon_value - baseline_value) / baseline_value) * 100.0
        rows.append(
            {
                "baseline_variant": baseline_case.get("execution_variant"),
                "myelon_variant": myelon_case.get("execution_variant"),
                "metric": metric,
                "baseline_value": baseline_value,
                "myelon_value": myelon_value,
                "delta_percent": round(delta_percent, 4) if delta_percent is not None else None,
                "baseline_status": baseline_case.get("case_status"),
                "myelon_status": myelon_case.get("case_status"),
            }
        )
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
    run_index_csv_path = reports_dir / "run_index.csv"
    run_index_md_path = reports_dir / "run_index.md"
    side_by_side_csv_path = reports_dir / "per_variant_side_by_side.csv"
    side_by_side_md_path = reports_dir / "per_variant_side_by_side.md"

    contract = report.get("benchmark_contract", {})
    case_rows = build_case_rows(report)
    run_index_rows = build_run_index_rows(report, report_path)
    side_by_side_rows = build_side_by_side_rows(report)
    fieldnames = sorted({key for row in case_rows for key in row.keys()}) if case_rows else [
        "label",
        "execution_variant",
        "stop_point",
        "skip_reason",
    ]
    _write_csv(case_csv_path, case_rows, fieldnames)
    _write_csv(
        run_index_csv_path,
        run_index_rows,
        [key for key in run_index_rows[0].keys()],
    )
    side_by_side_fieldnames = (
        [key for key in side_by_side_rows[0].keys()]
        if side_by_side_rows
        else [
            "baseline_variant",
            "myelon_variant",
            "metric",
            "baseline_value",
            "myelon_value",
            "delta_percent",
        ]
    )
    _write_csv(side_by_side_csv_path, side_by_side_rows, side_by_side_fieldnames)

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
        f"| status | {report.get('status')} |",
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
    run_index_lines = [
        "# Run Index",
        "",
        "| Key | Value |",
        "| --- | --- |",
    ]
    for key, value in run_index_rows[0].items():
        run_index_lines.append(f"| {key} | {value} |")
    run_index_md_path.write_text("\n".join(run_index_lines) + "\n", encoding="utf-8")

    side_by_side_lines = [
        "# Per-Variant Side By Side",
        "",
    ]
    if side_by_side_rows:
        side_header = side_by_side_fieldnames
        side_by_side_lines.append("| " + " | ".join(side_header) + " |")
        side_by_side_lines.append("| " + " | ".join("---" for _ in side_header) + " |")
        for row in side_by_side_rows:
            side_by_side_lines.append(
                "| " + " | ".join(str(row.get(name, "")) for name in side_header) + " |"
            )
    else:
        side_by_side_lines.append("No runner/Myelon comparison pair was available.")
    side_by_side_md_path.write_text("\n".join(side_by_side_lines) + "\n", encoding="utf-8")

    return {
        "summary_md": str(summary_md_path),
        "details_csv": str(case_csv_path),
        "run_index_csv": str(run_index_csv_path),
        "run_index_md": str(run_index_md_path),
        "side_by_side_csv": str(side_by_side_csv_path),
        "side_by_side_md": str(side_by_side_md_path),
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
