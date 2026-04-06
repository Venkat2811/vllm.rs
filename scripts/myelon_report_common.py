#!/usr/bin/env python3
import csv
import json
import re
import subprocess
from pathlib import Path

from tabulate import tabulate

from myelon_validation_common import (
    classify_arrival_pattern,
    classify_model_capability,
    extract_server_kvcache_plan,
    infer_pd_transport_mode,
    infer_request_run_class,
    infer_tp_scale_contract_fields,
    infer_workload_class_from_path,
)


RUNTIME_RE = re.compile(r"^runtime_sec = ([0-9.]+)$", re.MULTILINE)
REQUEST_RATE_RE = re.compile(r"^requests_per_sec = ([0-9.]+)$", re.MULTILINE)
LOGGED_AVG_LINE_RE = re.compile(
    r"^.*\[(ttft_ms|tpot_ms|latency_ms)\s*\]\s+avg:\s+([0-9.]+),\s+min:\s+([0-9.]+),\s+max:\s+([0-9.]+)$",
    re.MULTILINE,
)
TRUNCATED_SUMMARY_ROW_RE = re.compile(
    r"^\s*(ttft_ms|tpot_ms|latency_ms)\s+[0-9.]+\s+([0-9.]+)\s+[0-9.]+\s+\.\.\.\s+[0-9.]+\s+[0-9.]+\s+([0-9.]+)$",
    re.MULTILINE,
)
CLIENT_DONE_RE = re.compile(r"Client \d+ is done \(num_successes=(\d+), num_failures=(\d+)\)")
CLIENT_NO_MORE_WORK_RE = re.compile(r"Client \d+ has no more work")
CLIENT_TERMINATION_SIGNAL_RE = re.compile(r"Client \d+ received a termination signal")
HTTP_422_REJECTION_RE = re.compile(r"Received HTTP status 422 ")
SCHEDULER_KVCACHE_RE = re.compile(
    r"GPU Kvcache: .* used ([0-9.]+)% \(([0-9.]+)GB/([0-9.]+)GB\); CPU swap used ([0-9.]+)% \(([0-9.]+)GB/([0-9.]+)GB\)"
)
PREFIX_CACHE_ENABLED_RE = re.compile(r"Prefix cache enabled: (\d+) blocks \((\d+) tokens\)\.")
PREFIX_CACHE_HIT_RE = re.compile(
    r"Prefix cache hit seq \d+ \((\d+) cached tokens, (\d+) blocks\)"
)
PREFILL_EVENT_RE = re.compile(
    r"Prefilling \[seq_id \d+\]: (\d+) tokens in ([0-9.]+)s \(([0-9.]+) tokens/s(?:, cache included)?\)"
)
PROMPT_METRIC_RE = re.compile(
    r"\[Seq \d+\].*Prompt: (\d+) tokens in ([0-9.]+)s \(([0-9.]+) t/s\)"
)
DECODE_METRIC_RE = re.compile(
    r"\[Seq \d+\].*Decoded: (\d+) tokens in ([0-9.]+)s \(([0-9.]+) t/s\)"
)
SWAP_OUT_ATTEMPT_RE = re.compile(r"Trying to swap out preempt Seq \d+")
DROPPED_REQUEST_RE = re.compile(r"drop the oldest active request")
STREAM_GENERATION_FAILED_RE = re.compile(r"Stream generation failed")
FIRST_TOKEN_PATH_RE = re.compile(
    r"\[Seq \d+\]\s+⏱️ FirstTokenPath: scheduler_wait_ms=(\d+) prefill_roundtrip_ms=(\d+) response_to_emit_ms=(\d+) ingress_to_emit_ms=(\d+)"
)
FIRST_TOKEN_FLUSH_RE = re.compile(
    r"\[Seq \d+\]\s+⏱️ FirstTokenFlush: emit_to_flush_ms=(\d+) kind=([a-z_]+)(?: emission_trace=missing)?"
)


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


def _markdown_table_from_pairs(
    pairs: list[tuple[object, object]],
    headers: tuple[str, str] = ("Key", "Value"),
) -> str:
    return tabulate(pairs, headers=headers, tablefmt="github")


def _markdown_table_from_rows(
    rows: list[dict[str, object]],
    fieldnames: list[str],
) -> str:
    values = [[row.get(name, "") for name in fieldnames] for row in rows]
    return tabulate(values, headers=fieldnames, tablefmt="github")


def _sorted_top_rows(
    rows: list[dict[str, object]],
    key: str,
    *,
    reverse: bool,
    limit: int = 5,
) -> list[dict[str, object]]:
    sortable = [row for row in rows if isinstance(row.get(key), (int, float))]
    sortable.sort(key=lambda row: float(row.get(key)), reverse=reverse)
    return sortable[:limit]


def _slugify(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unspecified"
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text or "unspecified"


def _write_grouped_report_bundle(
    group_root: Path,
    title: str,
    identity_key: str,
    identity_value: object,
    findings_rows: list[dict[str, object]],
    findings_fields: list[str],
    detailed_rows: list[dict[str, object]],
    detailed_fields: list[str],
    findings_stem: str = "findings",
) -> None:
    group_root.mkdir(parents=True, exist_ok=True)

    findings_csv_path = group_root / f"{findings_stem}.csv"
    findings_md_path = group_root / f"{findings_stem}.md"
    side_csv_path = group_root / "per_model_side_by_side.csv"
    side_md_path = group_root / "per_model_side_by_side.md"

    _write_csv(findings_csv_path, findings_rows, findings_fields)
    _write_csv(side_csv_path, detailed_rows, detailed_fields)

    status_counts: dict[str, int] = {}
    for row in findings_rows:
        key = str(row.get("status"))
        status_counts[key] = status_counts.get(key, 0) + 1

    findings_lines = [
        f"# {title}",
        "",
        f"- {identity_key}: `{identity_value}`",
        f"- retained_runs: `{len(findings_rows)}`",
        "",
        "## Status Counts",
        "",
    ]
    if status_counts:
        status_rows = [
            {"status": key, "count": value}
            for key, value in sorted(status_counts.items())
        ]
        findings_lines.append(_markdown_table_from_rows(status_rows, ["status", "count"]))
    else:
        findings_lines.append("No retained runs were available.")
    findings_lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )
    if findings_rows:
        findings_lines.append(_markdown_table_from_rows(findings_rows, findings_fields))
    else:
        findings_lines.append("No retained runs were available.")
    findings_md_path.write_text("\n".join(findings_lines) + "\n", encoding="utf-8")

    side_lines = [
        f"# {title} Side By Side",
        "",
        f"- {identity_key}: `{identity_value}`",
        "",
    ]
    if detailed_rows:
        side_lines.append(_markdown_table_from_rows(detailed_rows, detailed_fields))
    else:
        side_lines.append("No baseline/Myelon comparison pairs were available.")
    side_md_path.write_text("\n".join(side_lines) + "\n", encoding="utf-8")


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

    machine_pairs = [
        (key, value)
        for key, value in machine_profile.items()
        if key != "gpu_inventory"
    ]
    repo_pairs = list(repo_state.items())
    lines = [
        "# System Snapshot",
        "",
        "## Key Facts",
        "",
        _markdown_table_from_pairs(machine_pairs),
        "",
        "## Repo State",
        "",
        _markdown_table_from_pairs(repo_pairs),
    ]
    if raw_captures:
        capture_pairs = [(key, value) for key, value in sorted(raw_captures.items())]
        lines.extend(
            [
                "",
                "## Raw Command Captures",
                "",
                _markdown_table_from_pairs(capture_pairs, headers=("Capture", "Path")),
            ]
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "md": str(md_path),
    }


def build_transport_settings(report: dict[str, object]) -> dict[str, object]:
    return {
        "build_features": report.get("build_features"),
        "effective_device_ids": report.get("effective_device_ids"),
        "myelon_rpc_depth": report.get("myelon_rpc_depth"),
        "myelon_response_depth": report.get("myelon_response_depth"),
        "myelon_busy_spin": report.get("myelon_busy_spin"),
        "prefix_cache_enabled": report.get("prefix_cache_enabled"),
        "prefix_cache_max_tokens": report.get("prefix_cache_max_tokens"),
        "kv_fraction": report.get("kv_fraction"),
        "cpu_mem_fold": report.get("cpu_mem_fold"),
        "no_stream": report.get("no_stream"),
    }


def _select_baseline_and_myelon_case_rows(
    case_rows: list[dict[str, object]],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
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
    return baseline_case, myelon_case


def _format_case_pair_field(
    case_rows: list[dict[str, object]],
    field_name: str,
) -> str | None:
    baseline_case, myelon_case = _select_baseline_and_myelon_case_rows(case_rows)
    baseline_value = (
        baseline_case.get(field_name) if isinstance(baseline_case, dict) else None
    )
    myelon_value = (
        myelon_case.get(field_name) if isinstance(myelon_case, dict) else None
    )
    if baseline_value in (None, "") and myelon_value in (None, ""):
        return None
    return f"{baseline_value or 'none'} -> {myelon_value or 'none'}"


def build_transport_settings_profile(report: dict[str, object]) -> str:
    contract = report.get("benchmark_contract", {})
    components = [str(contract.get("transport_mode") or "unspecified_transport")]
    rpc_depth = report.get("myelon_rpc_depth")
    response_depth = report.get("myelon_response_depth")
    busy_spin = report.get("myelon_busy_spin")
    prefix_cache_enabled = report.get("prefix_cache_enabled")
    prefix_cache_max_tokens = report.get("prefix_cache_max_tokens")
    kv_fraction = report.get("kv_fraction")
    cpu_mem_fold = report.get("cpu_mem_fold")

    if rpc_depth is not None:
        components.append(f"rpc{rpc_depth}")
    if response_depth is not None:
        components.append(f"resp{response_depth}")
    if busy_spin is not None:
        components.append("busy_spin" if busy_spin else "blocking_wait")
    if prefix_cache_enabled:
        if prefix_cache_max_tokens is not None:
            components.append(f"prefix{prefix_cache_max_tokens}")
        else:
            components.append("prefix_on")
    else:
        components.append("prefix_off")
    if kv_fraction is not None:
        components.append(f"kv{kv_fraction}")
    if cpu_mem_fold is not None:
        components.append(f"cpufold{cpu_mem_fold}")
    return "/".join(components)


def build_artifact_class(report: dict[str, object]) -> str:
    contract = report.get("benchmark_contract", {})
    run_class = contract.get("run_class") or "unspecified_run_class"
    result_boundary = report.get("result_boundary") or "unspecified_boundary"
    stop_point = contract.get("stop_point") or "full_completion"
    return f"{run_class}/{result_boundary}/{stop_point}"


def _classify_skip_boundary(skip_reason: object) -> str | None:
    if not isinstance(skip_reason, str) or not skip_reason.strip():
        return None
    if skip_reason.startswith("unsupported_architecture_"):
        return "architecture_limited"
    if skip_reason.startswith("unsupported_topology_"):
        return "topology_limited"
    if skip_reason.startswith("unsupported_transport_"):
        return "transport_limited"
    if skip_reason.startswith("swap_pressure_profile_"):
        return "configuration_limited"
    return "skip_limited"


def infer_case_result_boundary(case: dict[str, object]) -> str:
    skip_boundary = _classify_skip_boundary(case.get("skip_reason"))
    if skip_boundary is not None:
        return skip_boundary

    stop_point = case.get("stop_point")
    if stop_point not in (None, "full_completion"):
        if stop_point in {"benchmark_timeout", "runtime_error_boundary"}:
            return "runtime_limited"
        if stop_point == "allocator_seq_capacity_collapse":
            return "configuration_limited"
        return "stop_point_limited"

    if case.get("benchmark_exit_code") not in (None, 0):
        return "benchmark_failed"

    return "benchmark_complete"


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
            "result_boundary": infer_case_result_boundary(case),
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
            row["first_prefill_seconds_mean"] = measured_summary.get(
                "first_prefill_seconds", {}
            ).get("mean")
            row["first_prefill_tps_mean"] = measured_summary.get(
                "first_prefill_tokens_per_second", {}
            ).get("mean")
            row["prompt_seconds_mean"] = measured_summary.get("prompt_seconds", {}).get("mean")
            row["prompt_tps_mean"] = measured_summary.get(
                "prompt_tokens_per_second", {}
            ).get("mean")
            row["decode_seconds_mean"] = measured_summary.get("decode_seconds", {}).get("mean")
            row["decode_tps_mean"] = measured_summary.get(
                "decode_tokens_per_second", {}
            ).get("mean")
        observed_cache_pressure = case.get("observed_cache_pressure") if isinstance(case, dict) else None
        if isinstance(observed_cache_pressure, dict):
            row["requested_cache_pressure_profile"] = observed_cache_pressure.get(
                "requested_cache_pressure_profile"
            )
            row["pressure_profile_outcome"] = observed_cache_pressure.get(
                "pressure_profile_outcome"
            )
            row["planned_gpu_blocks"] = observed_cache_pressure.get(
                "planned_gpu_blocks"
            )
            row["planned_usable_kvcache_tokens"] = observed_cache_pressure.get(
                "planned_usable_kvcache_tokens"
            )
            row["planned_max_seqs"] = observed_cache_pressure.get(
                "planned_max_seqs"
            )
            row["planned_tokens_per_seq_limit"] = observed_cache_pressure.get(
                "planned_tokens_per_seq_limit"
            )
            row["configured_prefix_cache_blocks"] = observed_cache_pressure.get(
                "configured_prefix_cache_blocks"
            )
            row["configured_prefix_cache_tokens"] = observed_cache_pressure.get(
                "configured_prefix_cache_tokens"
            )
            row["observed_gpu_kv_usage_percent_max"] = observed_cache_pressure.get(
                "observed_gpu_kv_usage_percent_max"
            )
            row["observed_gpu_kv_usage_gb_max"] = observed_cache_pressure.get(
                "observed_gpu_kv_usage_gb_max"
            )
            row["observed_gpu_kv_budget_gb"] = observed_cache_pressure.get(
                "observed_gpu_kv_budget_gb"
            )
            row["observed_cpu_swap_usage_percent_max"] = observed_cache_pressure.get(
                "observed_cpu_swap_usage_percent_max"
            )
            row["observed_cpu_swap_usage_gb_max"] = observed_cache_pressure.get(
                "observed_cpu_swap_usage_gb_max"
            )
            row["observed_cpu_swap_budget_gb"] = observed_cache_pressure.get(
                "observed_cpu_swap_budget_gb"
            )
            row["observed_prefix_cache_miss_count"] = observed_cache_pressure.get(
                "observed_prefix_cache_miss_count"
            )
            row["observed_prefix_cache_insert_count"] = observed_cache_pressure.get(
                "observed_prefix_cache_insert_count"
            )
            row["observed_prefix_cache_eviction_count"] = observed_cache_pressure.get(
                "observed_prefix_cache_eviction_count"
            )
            row["observed_cache_pressure_level"] = observed_cache_pressure.get(
                "observed_cache_pressure_level"
            )
        observed_benchmark_outcome = (
            case.get("observed_benchmark_outcome") if isinstance(case, dict) else None
        )
        if isinstance(observed_benchmark_outcome, dict):
            row["observed_client_done_count"] = observed_benchmark_outcome.get(
                "observed_client_done_count"
            )
            row["observed_successful_requests_total"] = observed_benchmark_outcome.get(
                "observed_successful_requests_total"
            )
            row["observed_failed_requests_total"] = observed_benchmark_outcome.get(
                "observed_failed_requests_total"
            )
            row["observed_clients_with_failures"] = observed_benchmark_outcome.get(
                "observed_clients_with_failures"
            )
            row["observed_client_no_more_work_count"] = observed_benchmark_outcome.get(
                "observed_client_no_more_work_count"
            )
            row["observed_client_termination_signal_count"] = observed_benchmark_outcome.get(
                "observed_client_termination_signal_count"
            )
            row["observed_http_422_rejection_count"] = observed_benchmark_outcome.get(
                "observed_http_422_rejection_count"
            )
            row["observed_request_rejections"] = observed_benchmark_outcome.get(
                "observed_request_rejections"
            )
        observed_server_path_attribution = (
            case.get("observed_server_path_attribution")
            if isinstance(case, dict)
            else None
        )
        if isinstance(observed_server_path_attribution, dict):
            row["observed_prefill_event_count"] = observed_server_path_attribution.get(
                "observed_prefill_event_count"
            )
            row["observed_prefill_tokens_total"] = observed_server_path_attribution.get(
                "observed_prefill_tokens_total"
            )
            row["observed_prefill_seconds_total"] = observed_server_path_attribution.get(
                "observed_prefill_seconds_total"
            )
            row["observed_prefill_seconds_mean"] = observed_server_path_attribution.get(
                "observed_prefill_seconds_mean"
            )
            row["observed_prefill_tps_mean"] = observed_server_path_attribution.get(
                "observed_prefill_tps_mean"
            )
            row["observed_prompt_metric_event_count"] = observed_server_path_attribution.get(
                "observed_prompt_metric_event_count"
            )
            row["observed_prompt_tokens_total"] = observed_server_path_attribution.get(
                "observed_prompt_tokens_total"
            )
            row["observed_prompt_seconds_total"] = observed_server_path_attribution.get(
                "observed_prompt_seconds_total"
            )
            row["observed_prompt_seconds_mean"] = observed_server_path_attribution.get(
                "observed_prompt_seconds_mean"
            )
            row["observed_prompt_tps_mean"] = observed_server_path_attribution.get(
                "observed_prompt_tps_mean"
            )
            row["observed_decode_metric_event_count"] = observed_server_path_attribution.get(
                "observed_decode_metric_event_count"
            )
            row["observed_decode_tokens_total"] = observed_server_path_attribution.get(
                "observed_decode_tokens_total"
            )
            row["observed_decode_seconds_total"] = observed_server_path_attribution.get(
                "observed_decode_seconds_total"
            )
            row["observed_decode_seconds_mean"] = observed_server_path_attribution.get(
                "observed_decode_seconds_mean"
            )
            row["observed_decode_tps_mean"] = observed_server_path_attribution.get(
                "observed_decode_tps_mean"
            )
            row["observed_first_token_path_event_count"] = observed_server_path_attribution.get(
                "observed_first_token_path_event_count"
            )
            row["observed_scheduler_wait_ms_total"] = observed_server_path_attribution.get(
                "observed_scheduler_wait_ms_total"
            )
            row["observed_scheduler_wait_ms_mean"] = observed_server_path_attribution.get(
                "observed_scheduler_wait_ms_mean"
            )
            row["observed_prefill_roundtrip_ms_total"] = observed_server_path_attribution.get(
                "observed_prefill_roundtrip_ms_total"
            )
            row["observed_prefill_roundtrip_ms_mean"] = observed_server_path_attribution.get(
                "observed_prefill_roundtrip_ms_mean"
            )
            row["observed_response_to_emit_ms_total"] = observed_server_path_attribution.get(
                "observed_response_to_emit_ms_total"
            )
            row["observed_response_to_emit_ms_mean"] = observed_server_path_attribution.get(
                "observed_response_to_emit_ms_mean"
            )
            row["observed_ingress_to_emit_ms_total"] = observed_server_path_attribution.get(
                "observed_ingress_to_emit_ms_total"
            )
            row["observed_ingress_to_emit_ms_mean"] = observed_server_path_attribution.get(
                "observed_ingress_to_emit_ms_mean"
            )
            row["observed_first_token_flush_count"] = observed_server_path_attribution.get(
                "observed_first_token_flush_count"
            )
            row["observed_emit_to_flush_ms_total"] = observed_server_path_attribution.get(
                "observed_emit_to_flush_ms_total"
            )
            row["observed_emit_to_flush_ms_mean"] = observed_server_path_attribution.get(
                "observed_emit_to_flush_ms_mean"
            )
            row["observed_prefix_cache_hit_count"] = observed_server_path_attribution.get(
                "observed_prefix_cache_hit_count"
            )
            row["observed_prefix_cache_hit_tokens_total"] = observed_server_path_attribution.get(
                "observed_prefix_cache_hit_tokens_total"
            )
            row["observed_swap_out_attempt_count"] = observed_server_path_attribution.get(
                "observed_swap_out_attempt_count"
            )
            row["observed_dropped_request_count"] = observed_server_path_attribution.get(
                "observed_dropped_request_count"
            )
            row["observed_stream_generation_failed_count"] = observed_server_path_attribution.get(
                "observed_stream_generation_failed_count"
            )
        rows.append(row)
    return rows


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _classify_observed_cache_pressure(
    gpu_usage_percent: float | None,
    cpu_swap_percent: float | None,
    eviction_count: int,
) -> str | None:
    if cpu_swap_percent is not None and cpu_swap_percent > 0.0:
        return "swap_engaged"
    if gpu_usage_percent is not None and gpu_usage_percent >= 90.0:
        if eviction_count > 0:
            return "high_gpu_pressure_prefix_eviction"
        return "high_gpu_pressure_no_swap"
    if eviction_count > 0:
        return "prefix_eviction"
    if gpu_usage_percent is None:
        return None
    if gpu_usage_percent >= 50.0:
        return "high_gpu_pressure"
    if gpu_usage_percent >= 10.0:
        return "moderate_gpu_pressure"
    if gpu_usage_percent > 0.0:
        return "minimal_pressure"
    return "no_observed_pressure"


def _classify_pressure_profile_outcome(
    requested_profile: str | None,
    observed_level: str | None,
) -> str | None:
    if requested_profile is None or requested_profile == "unspecified":
        return None
    if requested_profile == "swap_pressure":
        if observed_level == "swap_engaged":
            return "requested_swap_achieved"
        if observed_level in {
            "high_gpu_pressure_no_swap",
            "high_gpu_pressure_prefix_eviction",
        }:
            return "requested_swap_reduced_to_gpu_pressure"
        return "requested_swap_not_observed"
    if requested_profile == "hard_thrash":
        if observed_level in {
            "swap_engaged",
            "high_gpu_pressure_no_swap",
            "high_gpu_pressure_prefix_eviction",
            "high_gpu_pressure",
        }:
            return "requested_thrash_observed"
        return "requested_thrash_not_observed"
    if requested_profile == "bounded_prefix":
        if observed_level in {"prefix_eviction", "minimal_pressure", "moderate_gpu_pressure"}:
            return "requested_prefix_control_observed"
        return "requested_prefix_control_not_observed"
    if requested_profile == "relaxed":
        if observed_level in {"minimal_pressure", "no_observed_pressure", None}:
            return "requested_relaxed_observed"
        return "requested_relaxed_exceeded"
    return None


def build_run_index_rows(report: dict[str, object], report_path: Path) -> list[dict[str, object]]:
    contract = report.get("benchmark_contract", {})
    machine_profile = report.get("machine_profile", {})
    model_capability = report.get("model_capability", {})
    transport_capability = report.get("transport_capability", {})
    concurrency_policy = contract.get("concurrency_policy", {})
    case_rows = build_case_rows(report)
    gpu_inventory = machine_profile.get("gpu_inventory", [])
    gpu_names = []
    if isinstance(gpu_inventory, list):
        gpu_names = [item.get("name") for item in gpu_inventory if isinstance(item, dict)]

    return [
        {
            "benchmark_family": contract.get("benchmark_family"),
            "benchmark_submode": contract.get("benchmark_submode"),
            "workload_class": contract.get("workload_class"),
            "warmup_policy": contract.get("warmup_policy"),
            "first_turn_measured": contract.get("first_turn_measured"),
            "arrival_pattern": contract.get("arrival_pattern"),
            "cache_pressure_profile": contract.get("cache_pressure_profile"),
            "equivalence_group": contract.get("equivalence_group"),
            "conversation_sampling": (
                concurrency_policy.get("conversation_sampling")
                if isinstance(concurrency_policy, dict)
                else None
            ),
            "limit_min_tokens": (
                concurrency_policy.get("limit_min_tokens")
                if isinstance(concurrency_policy, dict)
                else None
            ),
            "limit_max_tokens": (
                concurrency_policy.get("limit_max_tokens")
                if isinstance(concurrency_policy, dict)
                else None
            ),
            "topology_overlay": contract.get("topology_overlay"),
            "tp_scale_overlay": contract.get("tp_scale_overlay"),
            "prefill_tp_size": contract.get("prefill_tp_size"),
            "decode_tp_size": contract.get("decode_tp_size"),
            "pd_enabled": contract.get("pd_enabled"),
            "pd_role_layout": contract.get("pd_role_layout"),
            "transport_mode": contract.get("transport_mode"),
            "build_features": report.get("build_features"),
            "effective_device_ids": report.get("effective_device_ids"),
            "myelon_rpc_depth": report.get("myelon_rpc_depth"),
            "myelon_response_depth": report.get("myelon_response_depth"),
            "myelon_busy_spin": report.get("myelon_busy_spin"),
            "prefix_cache_enabled": report.get("prefix_cache_enabled"),
            "prefix_cache_max_tokens": report.get("prefix_cache_max_tokens"),
            "kv_fraction": report.get("kv_fraction"),
            "cpu_mem_fold": report.get("cpu_mem_fold"),
            "transport_settings_profile": build_transport_settings_profile(report),
            "run_class": contract.get("run_class"),
            "status": report.get("status"),
            "result_boundary": report.get("result_boundary"),
            "artifact_class": build_artifact_class(report),
            "expected_case_count": report.get("expected_case_count"),
            "observed_case_count": len(
                [case for case in report.get("cases", []) if isinstance(case, dict)]
            ),
            "stop_point": contract.get("stop_point"),
            "skip_reason": contract.get("skip_reason"),
            "pressure_profile_outcome_pair": _format_case_pair_field(
                case_rows,
                "pressure_profile_outcome",
            ),
            "observed_cache_pressure_level_pair": _format_case_pair_field(
                case_rows,
                "observed_cache_pressure_level",
            ),
            "transport_supported": transport_capability.get("pd_supported"),
            "transport_skip_reason": transport_capability.get("pd_skip_reason"),
            "host": machine_profile.get("hostname"),
            "gpu_names": ",".join(str(item) for item in gpu_names if item),
            "model_label": model_capability.get("model_label"),
            "model_architecture": model_capability.get("architecture"),
            "pd_supported": model_capability.get("pd_supported"),
            "report_json": str(report_path),
        }
    ]


def infer_report_status(report: dict[str, object]) -> str:
    expected_case_count = report.get("expected_case_count")
    observed_case_count = len(
        [case for case in report.get("cases", []) if isinstance(case, dict)]
    )
    if isinstance(expected_case_count, int) and observed_case_count < expected_case_count:
        return "partial"
    existing = report.get("status")
    if isinstance(existing, str) and existing.strip() and existing not in {
        "completed",
        "partial",
    }:
        return existing
    contract = report.get("benchmark_contract", {})
    if isinstance(contract, dict) and contract.get("skip_reason"):
        return "skipped"
    contract_stop_point = None
    if isinstance(contract, dict):
        contract_stop_point = contract.get("stop_point")
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        if case.get("skip_reason"):
            return "partial"
        case_stop_point = case.get("stop_point")
        if case_stop_point not in (None, "full_completion"):
            # Planned stop-point probes are complete evidence within their
            # configured boundary; result_boundary carries that distinction.
            if contract_stop_point in (None, case_stop_point):
                continue
            return "partial"
        if case.get("benchmark_exit_code") not in (None, 0):
            return "partial"
    return "completed"


def infer_report_result_boundary(report: dict[str, object]) -> str:
    contract = report.get("benchmark_contract", {})
    if isinstance(contract, dict):
        skip_boundary = _classify_skip_boundary(contract.get("skip_reason"))
        if skip_boundary is not None:
            return skip_boundary

    status = report.get("status")
    if status == "skipped_unsupported_architecture":
        return "architecture_limited"
    if status == "skipped_unsupported_topology":
        return "topology_limited"
    if status == "skipped_unsupported_transport":
        return "transport_limited"

    boundaries = []
    for case in report.get("cases", []):
        if isinstance(case, dict):
            boundaries.append(infer_case_result_boundary(case))

    if not boundaries:
        return "benchmark_complete"

    priority = [
        "architecture_limited",
        "topology_limited",
        "transport_limited",
        "configuration_limited",
        "runtime_limited",
        "benchmark_failed",
        "stop_point_limited",
        "skip_limited",
        "benchmark_complete",
    ]
    for candidate in priority:
        if candidate in boundaries:
            return candidate
    return "benchmark_complete"


def infer_benchmark_contract(report: dict[str, object]) -> dict[str, object]:
    existing = report.get("benchmark_contract")
    if isinstance(existing, dict) and existing:
        contract = dict(existing)
        tp_fields = infer_tp_scale_contract_fields(
            str(contract.get("topology_overlay", "")),
            contract.get("transport_mode"),
        )
        for key, value in tp_fields.items():
            if contract.get(key) is None:
                contract[key] = value
        return contract

    workload_file = str(report.get("workload_file", ""))
    workload_class = infer_workload_class_from_path(workload_file)
    warmup_step = bool(report.get("warmup_step", False))
    max_num_requests = report.get("max_num_requests")
    if isinstance(max_num_requests, int) and max_num_requests <= 0:
        max_num_requests = None
    run_class = infer_request_run_class(max_num_requests)
    request_rate = report.get("request_rate", 0)

    if report.get("pd_url") is not None or report.get("server_device_ids") is not None:
        return {
            "benchmark_family": "pd_qos",
            "benchmark_submode": (
                "first_transfer_control"
                if workload_class == "pd_first_transfer_control"
                else ("warm_steady_state" if warmup_step else "cold_turn")
            ),
            "question_answered": "How does Myelon affect PD-capable serving paths on supported transports and models?",
            "workload_class": workload_class,
            "warmup_policy": "warmup_step_skips_first_turn" if warmup_step else "measure_first_turn",
            "first_turn_measured": not warmup_step,
            "arrival_pattern": classify_arrival_pattern(request_rate),
            "concurrency_policy": {
                "driver": "pd_server_client_http",
                "max_num_seqs": report.get("max_num_seqs"),
                "num_clients": report.get("num_clients"),
                "max_active_conversations": report.get("max_active_conversations"),
                "max_num_requests": max_num_requests,
                "max_turns": report.get("max_turns"),
                "request_rate": request_rate,
            },
            "topology_overlay": "pd_tp1",
            "tp_scale_overlay": "pd(tp1/tp1)",
            "prefill_tp_size": 1,
            "decode_tp_size": 1,
            "pd_enabled": True,
            "pd_role_layout": "same_host_split_roles",
            "transport_mode": infer_pd_transport_mode(report.get("pd_url")),
            "run_class": run_class,
            "cache_pressure_profile": "unspecified",
            "equivalence_group": None,
            "stop_point": "full_completion",
            "skip_reason": None,
        }

    if "mode" in report and "cases" in report:
        mode = str(report.get("mode"))
        benchmark_family = str(report.get("benchmark_family", "serving_qos"))
        benchmark_submode = str(
            report.get(
                "benchmark_submode",
                "warm_steady_state" if warmup_step else "cold_turn",
            )
        )
        return {
        "benchmark_family": benchmark_family,
        "benchmark_submode": benchmark_submode,
        "question_answered": (
            "What user-facing QoS difference does Myelon produce in persistent serving?"
            if benchmark_family == "serving_qos"
                else "How much shared-memory gain survives when the full server path stays in the loop under cache-hostile, prefill-dominant conditions?"
            ),
            "workload_class": workload_class,
            "warmup_policy": "warmup_step_skips_first_turn" if warmup_step else "measure_first_turn",
            "first_turn_measured": not warmup_step,
            "arrival_pattern": classify_arrival_pattern(request_rate),
            "concurrency_policy": {
                "driver": "persistent_http_server",
                "max_num_seqs": report.get("max_num_seqs"),
                "num_clients": report.get("num_clients"),
                "max_active_conversations": report.get("max_active_conversations"),
                "max_num_requests": max_num_requests,
                "max_turns": report.get("max_turns"),
                "request_rate": request_rate,
                "conversation_sampling": report.get("conversation_sampling"),
                "limit_min_tokens": report.get("limit_min_tokens"),
                "limit_max_tokens": report.get("limit_max_tokens"),
                "mode": mode,
            },
            "cache_pressure_profile": report.get("cache_pressure_profile", "unspecified"),
            "equivalence_group": (
                "fixed_prompt_burst_bridge"
                if benchmark_family == "server_prefill_stress"
                and benchmark_submode == "fixed_prompt_burst"
                else None
            ),
            "topology_overlay": mode,
            "tp_scale_overlay": "tp1" if mode == "single_gpu" else "tp2",
            "prefill_tp_size": 1 if mode == "single_gpu" else 2,
            "decode_tp_size": 1 if mode == "single_gpu" else 2,
            "pd_enabled": False,
            "pd_role_layout": None,
            "transport_mode": "socket_vs_myelon_process_runner",
            "run_class": run_class,
            "stop_point": "full_completion",
            "skip_reason": None,
        }

    return {
        "benchmark_family": "prefill_stress",
        "benchmark_submode": "legacy_cli",
        "question_answered": "Does Myelon materially improve transport-sensitive prompt or prefill paths?",
        "workload_class": workload_class or "file_defined",
        "warmup_policy": "legacy_cli_unspecified",
        "first_turn_measured": True,
        "arrival_pattern": "prompt_burst_serial_runs",
        "concurrency_policy": {
            "driver": "legacy_cli",
        },
        "cache_pressure_profile": "unspecified",
        "equivalence_group": None,
        "topology_overlay": str(report.get("mode", "legacy_cli")),
        "tp_scale_overlay": (
            "tp1"
            if str(report.get("mode", "legacy_cli")) == "single_gpu"
            else str(report.get("mode", "legacy_cli"))
        ),
        "prefill_tp_size": (
            1 if str(report.get("mode", "legacy_cli")) == "single_gpu" else None
        ),
        "decode_tp_size": (
            1 if str(report.get("mode", "legacy_cli")) == "single_gpu" else None
        ),
        "pd_enabled": False,
        "pd_role_layout": None,
        "transport_mode": "socket_vs_myelon_process_runner",
        "run_class": "quickpass",
        "stop_point": "full_completion",
        "skip_reason": None,
    }


def infer_machine_profile(report: dict[str, object]) -> dict[str, object]:
    existing = report.get("machine_profile")
    if isinstance(existing, dict) and existing:
        return existing
    return {
        "hostname": None,
        "gpu_inventory": [],
        "detected_cuda_device_count": report.get("detected_cuda_device_count"),
        "effective_device_ids": report.get("effective_device_ids"),
    }


def infer_model_capability(report: dict[str, object]) -> dict[str, object]:
    existing = report.get("model_capability")
    if isinstance(existing, dict) and existing:
        return existing
    model_path = report.get("model_path")
    if isinstance(model_path, str) and model_path:
        return classify_model_capability(model_path)
    return {
        "model_label": None,
        "architecture": None,
        "architectures": [],
        "model_type": None,
        "layer_types": [],
        "pd_supported": None,
        "pd_skip_reason": None,
    }


def _backfill_case_summary_from_benchmark_log(case: dict[str, object]) -> None:
    summary = case.get("summary")
    if not isinstance(summary, dict):
        summary = {
            "runtime_sec": None,
            "requests_per_sec": None,
            "warmup_runtime_sec": None,
            "total_runtime_incl_warmup_sec": None,
            "table": {},
        }
        case["summary"] = summary

    table = summary.get("table")
    if not isinstance(table, dict):
        table = {}
        summary["table"] = table

    if all(metric in table for metric in ("ttft_ms", "tpot_ms", "latency_ms")):
        return

    benchmark_log_path = case.get("benchmark_log_path")
    if not isinstance(benchmark_log_path, str) or not benchmark_log_path:
        return

    path = Path(benchmark_log_path)
    if not path.is_file():
        return

    text = path.read_text(encoding="utf-8")
    if summary.get("runtime_sec") is None:
        runtime_match = RUNTIME_RE.search(text)
        if runtime_match:
            summary["runtime_sec"] = float(runtime_match.group(1))
    if summary.get("requests_per_sec") is None:
        request_rate_match = REQUEST_RATE_RE.search(text)
        if request_rate_match:
            summary["requests_per_sec"] = float(request_rate_match.group(1))

    for match in LOGGED_AVG_LINE_RE.finditer(text):
        metric_name = match.group(1)
        if metric_name in table:
            continue
        table[metric_name] = {
            "mean": float(match.group(2)),
            "min": float(match.group(3)),
            "max": float(match.group(4)),
        }
    for match in TRUNCATED_SUMMARY_ROW_RE.finditer(text):
        metric_name = match.group(1)
        if metric_name in table:
            continue
        table[metric_name] = {
            "mean": float(match.group(2)),
            "max": float(match.group(3)),
        }


def _backfill_case_benchmark_outcome_from_benchmark_log(case: dict[str, object]) -> None:
    existing = case.get("observed_benchmark_outcome")
    if isinstance(existing, dict) and existing:
        return

    benchmark_log_path = case.get("benchmark_log_path")
    if not isinstance(benchmark_log_path, str) or not benchmark_log_path:
        return

    path = Path(benchmark_log_path)
    if not path.is_file():
        return

    text = path.read_text(encoding="utf-8", errors="replace")
    client_done_matches = CLIENT_DONE_RE.findall(text)
    success_total = sum(int(successes) for successes, _ in client_done_matches)
    failure_total = sum(int(failures) for _, failures in client_done_matches)
    clients_with_failures = sum(
        1 for _, failures in client_done_matches if int(failures) > 0
    )
    client_done_count = len(client_done_matches)
    no_more_work_count = len(CLIENT_NO_MORE_WORK_RE.findall(text))
    termination_signal_count = len(CLIENT_TERMINATION_SIGNAL_RE.findall(text))
    http_422_rejection_count = len(HTTP_422_REJECTION_RE.findall(text))

    if (
        client_done_count == 0
        and no_more_work_count == 0
        and termination_signal_count == 0
        and http_422_rejection_count == 0
    ):
        return

    case["observed_benchmark_outcome"] = {
        "observed_client_done_count": client_done_count,
        "observed_successful_requests_total": success_total,
        "observed_failed_requests_total": failure_total,
        "observed_clients_with_failures": clients_with_failures,
        "observed_client_no_more_work_count": no_more_work_count,
        "observed_client_termination_signal_count": termination_signal_count,
        "observed_http_422_rejection_count": http_422_rejection_count,
        "observed_request_rejections": (
            http_422_rejection_count > 0 or failure_total > 0
        ),
    }


def _summarize_triplet_matches(
    matches: list[tuple[str, str, str]],
) -> dict[str, float | int] | None:
    if not matches:
        return None

    tokens = [int(token_count) for token_count, _, _ in matches]
    seconds = [float(seconds_value) for _, seconds_value, _ in matches]
    rates = [float(rate_value) for _, _, rate_value in matches]
    return {
        "count": len(matches),
        "tokens_total": sum(tokens),
        "seconds_total": round(sum(seconds), 3),
        "seconds_mean": round(sum(seconds) / len(seconds), 3),
        "tokens_per_second_mean": round(sum(rates) / len(rates), 3),
    }


def _summarize_numeric_values(values: list[float | int]) -> dict[str, float | int] | None:
    if not values:
        return None
    total = float(sum(values))
    if all(isinstance(value, int) for value in values):
        total_value: float | int = int(total)
    else:
        total_value = round(total, 3)
    return {
        "count": len(values),
        "total": total_value,
        "mean": round(total / len(values), 3),
    }


def _backfill_case_server_path_attribution(case: dict[str, object]) -> None:
    existing = case.get("observed_server_path_attribution")
    if isinstance(existing, dict) and existing:
        return

    server_log_path = case.get("server_log_path")
    if not isinstance(server_log_path, str) or not server_log_path:
        return

    path = Path(server_log_path)
    if not path.is_file():
        return

    text = path.read_text(encoding="utf-8", errors="replace")
    prefill_matches = PREFILL_EVENT_RE.findall(text)
    prompt_matches = PROMPT_METRIC_RE.findall(text)
    decode_matches = DECODE_METRIC_RE.findall(text)
    prefix_cache_hit_matches = PREFIX_CACHE_HIT_RE.findall(text)
    first_token_path_matches = FIRST_TOKEN_PATH_RE.findall(text)
    first_token_flush_matches = FIRST_TOKEN_FLUSH_RE.findall(text)
    swap_out_attempt_count = len(SWAP_OUT_ATTEMPT_RE.findall(text))
    dropped_request_count = len(DROPPED_REQUEST_RE.findall(text))
    stream_generation_failed_count = len(STREAM_GENERATION_FAILED_RE.findall(text))

    if not any(
        (
            prefill_matches,
            prompt_matches,
            decode_matches,
            prefix_cache_hit_matches,
            first_token_path_matches,
            first_token_flush_matches,
            swap_out_attempt_count,
            dropped_request_count,
            stream_generation_failed_count,
        )
    ):
        return

    attribution: dict[str, float | int] = {
        "observed_swap_out_attempt_count": swap_out_attempt_count,
        "observed_dropped_request_count": dropped_request_count,
        "observed_stream_generation_failed_count": stream_generation_failed_count,
        "observed_prefix_cache_hit_count": len(prefix_cache_hit_matches),
        "observed_prefix_cache_hit_tokens_total": sum(
            int(token_count) for token_count, _ in prefix_cache_hit_matches
        ),
    }

    prefill_summary = _summarize_triplet_matches(prefill_matches)
    if prefill_summary is not None:
        attribution.update(
            {
                "observed_prefill_event_count": prefill_summary["count"],
                "observed_prefill_tokens_total": prefill_summary["tokens_total"],
                "observed_prefill_seconds_total": prefill_summary["seconds_total"],
                "observed_prefill_seconds_mean": prefill_summary["seconds_mean"],
                "observed_prefill_tps_mean": prefill_summary[
                    "tokens_per_second_mean"
                ],
            }
        )

    prompt_summary = _summarize_triplet_matches(prompt_matches)
    if prompt_summary is not None:
        attribution.update(
            {
                "observed_prompt_metric_event_count": prompt_summary["count"],
                "observed_prompt_tokens_total": prompt_summary["tokens_total"],
                "observed_prompt_seconds_total": prompt_summary["seconds_total"],
                "observed_prompt_seconds_mean": prompt_summary["seconds_mean"],
                "observed_prompt_tps_mean": prompt_summary[
                    "tokens_per_second_mean"
                ],
            }
        )

    decode_summary = _summarize_triplet_matches(decode_matches)
    if decode_summary is not None:
        attribution.update(
            {
                "observed_decode_metric_event_count": decode_summary["count"],
                "observed_decode_tokens_total": decode_summary["tokens_total"],
                "observed_decode_seconds_total": decode_summary["seconds_total"],
                "observed_decode_seconds_mean": decode_summary["seconds_mean"],
                "observed_decode_tps_mean": decode_summary[
                    "tokens_per_second_mean"
                ],
            }
        )

    if first_token_path_matches:
        scheduler_wait_summary = _summarize_numeric_values(
            [int(wait_ms) for wait_ms, _, _, _ in first_token_path_matches]
        )
        prefill_roundtrip_summary = _summarize_numeric_values(
            [int(roundtrip_ms) for _, roundtrip_ms, _, _ in first_token_path_matches]
        )
        response_to_emit_summary = _summarize_numeric_values(
            [int(response_ms) for _, _, response_ms, _ in first_token_path_matches]
        )
        ingress_to_emit_summary = _summarize_numeric_values(
            [int(ingress_ms) for _, _, _, ingress_ms in first_token_path_matches]
        )
        attribution["observed_first_token_path_event_count"] = len(first_token_path_matches)
        if scheduler_wait_summary is not None:
            attribution["observed_scheduler_wait_ms_total"] = scheduler_wait_summary["total"]
            attribution["observed_scheduler_wait_ms_mean"] = scheduler_wait_summary["mean"]
        if prefill_roundtrip_summary is not None:
            attribution["observed_prefill_roundtrip_ms_total"] = prefill_roundtrip_summary["total"]
            attribution["observed_prefill_roundtrip_ms_mean"] = prefill_roundtrip_summary["mean"]
        if response_to_emit_summary is not None:
            attribution["observed_response_to_emit_ms_total"] = response_to_emit_summary["total"]
            attribution["observed_response_to_emit_ms_mean"] = response_to_emit_summary["mean"]
        if ingress_to_emit_summary is not None:
            attribution["observed_ingress_to_emit_ms_total"] = ingress_to_emit_summary["total"]
            attribution["observed_ingress_to_emit_ms_mean"] = ingress_to_emit_summary["mean"]

    if first_token_flush_matches:
        emit_to_flush_summary = _summarize_numeric_values(
            [int(flush_ms) for flush_ms, _ in first_token_flush_matches]
        )
        attribution["observed_first_token_flush_count"] = len(first_token_flush_matches)
        if emit_to_flush_summary is not None:
            attribution["observed_emit_to_flush_ms_total"] = emit_to_flush_summary["total"]
            attribution["observed_emit_to_flush_ms_mean"] = emit_to_flush_summary["mean"]

    case["observed_server_path_attribution"] = attribution


def _merge_case_observed_fields_into_summary(case: dict[str, object]) -> None:
    summary = case.get("summary")
    if not isinstance(summary, dict):
        return

    observed_cache_pressure = case.get("observed_cache_pressure")
    if isinstance(observed_cache_pressure, dict):
        summary["observed_cache_pressure"] = observed_cache_pressure

    observed_benchmark_outcome = case.get("observed_benchmark_outcome")
    if isinstance(observed_benchmark_outcome, dict):
        summary["observed_benchmark_outcome"] = observed_benchmark_outcome

    observed_server_path_attribution = case.get("observed_server_path_attribution")
    if isinstance(observed_server_path_attribution, dict):
        summary["observed_server_path_attribution"] = observed_server_path_attribution


def _backfill_case_observed_cache_pressure(
    case: dict[str, object],
    default_requested_profile: str | None = None,
) -> None:
    existing = case.get("observed_cache_pressure")
    if isinstance(existing, dict) and existing:
        return

    server_log_path = case.get("server_log_path")
    if not isinstance(server_log_path, str) or not server_log_path:
        return

    path = Path(server_log_path)
    if not path.is_file():
        return

    planned_kvcache = extract_server_kvcache_plan(path)
    configured_prefix_cache_blocks = None
    configured_prefix_cache_tokens = None
    max_gpu_usage_percent = None
    max_gpu_usage_gb = None
    gpu_budget_gb = None
    max_cpu_swap_percent = None
    max_cpu_swap_gb = None
    cpu_swap_budget_gb = None
    prefix_cache_miss_count = 0
    prefix_cache_insert_count = 0
    prefix_cache_eviction_count = 0

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "Prefix cache miss seq " in line:
            prefix_cache_miss_count += 1
        if "Prefix cache insert seq " in line:
            prefix_cache_insert_count += 1
        if "Prefix cache evict" in line or "Prefix cache eviction" in line:
            prefix_cache_eviction_count += 1

        prefix_match = PREFIX_CACHE_ENABLED_RE.search(line)
        if prefix_match:
            configured_prefix_cache_blocks = int(prefix_match.group(1))
            configured_prefix_cache_tokens = int(prefix_match.group(2))

        scheduler_match = SCHEDULER_KVCACHE_RE.search(line)
        if scheduler_match:
            gpu_usage_percent = float(scheduler_match.group(1))
            gpu_usage_gb = float(scheduler_match.group(2))
            gpu_budget = float(scheduler_match.group(3))
            cpu_swap_percent = float(scheduler_match.group(4))
            cpu_swap_gb = float(scheduler_match.group(5))
            cpu_budget = float(scheduler_match.group(6))

            max_gpu_usage_percent = (
                gpu_usage_percent
                if max_gpu_usage_percent is None
                else max(max_gpu_usage_percent, gpu_usage_percent)
            )
            max_gpu_usage_gb = (
                gpu_usage_gb
                if max_gpu_usage_gb is None
                else max(max_gpu_usage_gb, gpu_usage_gb)
            )
            max_cpu_swap_percent = (
                cpu_swap_percent
                if max_cpu_swap_percent is None
                else max(max_cpu_swap_percent, cpu_swap_percent)
            )
            max_cpu_swap_gb = (
                cpu_swap_gb
                if max_cpu_swap_gb is None
                else max(max_cpu_swap_gb, cpu_swap_gb)
            )
            gpu_budget_gb = gpu_budget
            cpu_swap_budget_gb = cpu_budget

    if all(
        value is None
        for value in (
            configured_prefix_cache_blocks,
            configured_prefix_cache_tokens,
            max_gpu_usage_percent,
            max_cpu_swap_percent,
        )
    ) and not any(
        (
            prefix_cache_miss_count,
            prefix_cache_insert_count,
            prefix_cache_eviction_count,
        )
    ):
        return

    requested_profile = case.get("cache_pressure_profile", default_requested_profile)
    observed_level = _classify_observed_cache_pressure(
        max_gpu_usage_percent,
        max_cpu_swap_percent,
        prefix_cache_eviction_count,
    )
    case["observed_cache_pressure"] = {
        "requested_cache_pressure_profile": requested_profile,
        "planned_gpu_blocks": (
            planned_kvcache.get("planned_gpu_blocks")
            if planned_kvcache is not None
            else None
        ),
        "planned_usable_kvcache_tokens": (
            planned_kvcache.get("planned_usable_kvcache_tokens")
            if planned_kvcache is not None
            else None
        ),
        "planned_max_seqs": (
            planned_kvcache.get("planned_max_seqs")
            if planned_kvcache is not None
            else None
        ),
        "planned_tokens_per_seq_limit": (
            planned_kvcache.get("planned_tokens_per_seq_limit")
            if planned_kvcache is not None
            else None
        ),
        "configured_prefix_cache_blocks": configured_prefix_cache_blocks,
        "configured_prefix_cache_tokens": configured_prefix_cache_tokens,
        "observed_gpu_kv_usage_percent_max": max_gpu_usage_percent,
        "observed_gpu_kv_usage_gb_max": max_gpu_usage_gb,
        "observed_gpu_kv_budget_gb": gpu_budget_gb,
        "observed_cpu_swap_usage_percent_max": max_cpu_swap_percent,
        "observed_cpu_swap_usage_gb_max": max_cpu_swap_gb,
        "observed_cpu_swap_budget_gb": cpu_swap_budget_gb,
        "observed_prefix_cache_miss_count": prefix_cache_miss_count,
        "observed_prefix_cache_insert_count": prefix_cache_insert_count,
        "observed_prefix_cache_eviction_count": prefix_cache_eviction_count,
        "observed_cache_pressure_level": observed_level,
        "pressure_profile_outcome": _classify_pressure_profile_outcome(
            requested_profile,
            observed_level,
        ),
    }


def normalize_report(report: dict[str, object]) -> dict[str, object]:
    normalized = json.loads(json.dumps(report))
    contract = infer_benchmark_contract(report)
    default_requested_profile = None
    if isinstance(contract, dict):
        default_requested_profile = contract.get("cache_pressure_profile")
    for case in normalized.get("cases", []):
        if isinstance(case, dict):
            _backfill_case_summary_from_benchmark_log(case)
            _backfill_case_observed_cache_pressure(case, default_requested_profile)
            _backfill_case_benchmark_outcome_from_benchmark_log(case)
            _backfill_case_server_path_attribution(case)
            _merge_case_observed_fields_into_summary(case)
    normalized["benchmark_contract"] = contract
    normalized["machine_profile"] = infer_machine_profile(report)
    normalized["model_capability"] = infer_model_capability(report)
    normalized["status"] = infer_report_status(normalized)
    normalized["result_boundary"] = infer_report_result_boundary(normalized)
    return normalized


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
        "first_prefill_seconds_mean",
        "first_prefill_tps_mean",
        "prompt_seconds_mean",
        "prompt_tps_mean",
        "decode_seconds_mean",
        "decode_tps_mean",
        "planned_max_seqs",
        "planned_usable_kvcache_tokens",
        "observed_gpu_kv_usage_percent_max",
        "observed_cpu_swap_usage_percent_max",
        "observed_prefix_cache_miss_count",
        "observed_prefix_cache_insert_count",
        "observed_prefix_cache_eviction_count",
        "observed_prefill_event_count",
        "observed_prefill_seconds_total",
        "observed_prefill_tps_mean",
        "observed_first_token_path_event_count",
        "observed_scheduler_wait_ms_total",
        "observed_scheduler_wait_ms_mean",
        "observed_prefill_roundtrip_ms_total",
        "observed_prefill_roundtrip_ms_mean",
        "observed_response_to_emit_ms_total",
        "observed_response_to_emit_ms_mean",
        "observed_ingress_to_emit_ms_total",
        "observed_ingress_to_emit_ms_mean",
        "observed_first_token_flush_count",
        "observed_emit_to_flush_ms_total",
        "observed_emit_to_flush_ms_mean",
        "observed_prompt_metric_event_count",
        "observed_prompt_seconds_total",
        "observed_prompt_tps_mean",
        "observed_decode_metric_event_count",
        "observed_decode_seconds_total",
        "observed_decode_tps_mean",
        "observed_prefix_cache_hit_count",
        "observed_swap_out_attempt_count",
        "observed_dropped_request_count",
        "observed_stream_generation_failed_count",
        "observed_successful_requests_total",
        "observed_failed_requests_total",
        "observed_clients_with_failures",
        "observed_http_422_rejection_count",
    ]
    for metric in metrics:
        baseline_value = _to_float(baseline_case.get(metric))
        myelon_value = _to_float(myelon_case.get(metric))
        if baseline_value is None and myelon_value is None:
            continue
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

    normalized_report = normalize_report(report)
    contract = normalized_report.get("benchmark_contract", {})
    case_rows = build_case_rows(normalized_report)
    run_index_rows = build_run_index_rows(normalized_report, report_path)
    side_by_side_rows = build_side_by_side_rows(normalized_report)
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

    summary_pairs = [
        ("benchmark_family", contract.get("benchmark_family")),
        ("benchmark_submode", contract.get("benchmark_submode")),
        ("workload_class", contract.get("workload_class")),
        ("warmup_policy", contract.get("warmup_policy")),
        ("first_turn_measured", contract.get("first_turn_measured")),
        ("arrival_pattern", contract.get("arrival_pattern")),
        ("cache_pressure_profile", contract.get("cache_pressure_profile")),
        ("equivalence_group", contract.get("equivalence_group")),
        (
            "conversation_sampling",
            contract.get("concurrency_policy", {}).get("conversation_sampling")
            if isinstance(contract.get("concurrency_policy"), dict)
            else None,
        ),
        (
            "limit_min_tokens",
            contract.get("concurrency_policy", {}).get("limit_min_tokens")
            if isinstance(contract.get("concurrency_policy"), dict)
            else None,
        ),
        (
            "limit_max_tokens",
            contract.get("concurrency_policy", {}).get("limit_max_tokens")
            if isinstance(contract.get("concurrency_policy"), dict)
            else None,
        ),
        ("topology_overlay", contract.get("topology_overlay")),
        ("tp_scale_overlay", contract.get("tp_scale_overlay")),
        ("prefill_tp_size", contract.get("prefill_tp_size")),
        ("decode_tp_size", contract.get("decode_tp_size")),
        ("pd_enabled", contract.get("pd_enabled")),
        ("pd_role_layout", contract.get("pd_role_layout")),
        ("transport_mode", contract.get("transport_mode")),
        ("build_features", report.get("build_features")),
        ("effective_device_ids", report.get("effective_device_ids")),
        ("myelon_rpc_depth", report.get("myelon_rpc_depth")),
        ("myelon_response_depth", report.get("myelon_response_depth")),
        ("myelon_busy_spin", report.get("myelon_busy_spin")),
        ("prefix_cache_enabled", report.get("prefix_cache_enabled")),
        ("prefix_cache_max_tokens", report.get("prefix_cache_max_tokens")),
        ("kv_fraction", report.get("kv_fraction")),
        ("cpu_mem_fold", report.get("cpu_mem_fold")),
        ("transport_settings_profile", build_transport_settings_profile(normalized_report)),
        ("run_class", contract.get("run_class")),
        ("result_boundary", normalized_report.get("result_boundary")),
        ("artifact_class", build_artifact_class(normalized_report)),
        ("stop_point", contract.get("stop_point")),
        ("status", normalized_report.get("status")),
        ("expected_case_count", normalized_report.get("expected_case_count")),
        (
            "observed_case_count",
            len(
                [
                    case
                    for case in normalized_report.get("cases", [])
                    if isinstance(case, dict)
                ]
            ),
        ),
        ("report_json", report_path),
    ]
    lines = [
        "# Benchmark Summary",
        "",
        _markdown_table_from_pairs(summary_pairs),
        "",
        "## Case Summary",
        "",
    ]

    if case_rows:
        lines.append(_markdown_table_from_rows(case_rows, fieldnames))
    else:
        lines.append("No case rows were available.")

    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run_index_lines = [
        "# Run Index",
        "",
        _markdown_table_from_pairs(list(run_index_rows[0].items())),
    ]
    run_index_md_path.write_text("\n".join(run_index_lines) + "\n", encoding="utf-8")

    side_by_side_lines = [
        "# Per-Variant Side By Side",
        "",
    ]
    if side_by_side_rows:
        side_by_side_lines.append(
            _markdown_table_from_rows(side_by_side_rows, side_by_side_fieldnames)
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


def write_bundle_manifest(
    output_root: Path,
    report: dict[str, object],
    report_path: Path,
    system_info: dict[str, str],
    benchmarks: dict[str, str],
) -> dict[str, str]:
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    normalized_report = normalize_report(report)
    contract = normalized_report.get("benchmark_contract", {})
    machine_profile = normalized_report.get("machine_profile", {})
    model_capability = normalized_report.get("model_capability", {})
    transport_settings = build_transport_settings(normalized_report)

    manifest = {
        "benchmark_family": contract.get("benchmark_family"),
        "benchmark_submode": contract.get("benchmark_submode"),
        "model_label": model_capability.get("model_label"),
        "topology_overlay": contract.get("topology_overlay"),
        "tp_scale_overlay": contract.get("tp_scale_overlay"),
        "prefill_tp_size": contract.get("prefill_tp_size"),
        "decode_tp_size": contract.get("decode_tp_size"),
        "pd_enabled": contract.get("pd_enabled"),
        "pd_role_layout": contract.get("pd_role_layout"),
        "transport_mode": contract.get("transport_mode"),
        "transport_settings_profile": build_transport_settings_profile(normalized_report),
        "run_class": contract.get("run_class"),
        "status": normalized_report.get("status"),
        "result_boundary": normalized_report.get("result_boundary"),
        "artifact_class": build_artifact_class(normalized_report),
        "stop_point": contract.get("stop_point"),
        "host": machine_profile.get("hostname"),
        "report_json": str(report_path),
        "transport_settings": transport_settings,
        "system_info": system_info,
        "benchmarks": benchmarks,
    }

    manifest_json_path = reports_dir / "manifest.json"
    manifest_md_path = reports_dir / "manifest.md"
    _write_json(manifest_json_path, manifest)

    manifest_pairs = [
        ("benchmark_family", manifest["benchmark_family"]),
        ("benchmark_submode", manifest["benchmark_submode"]),
        ("model_label", manifest["model_label"]),
        ("topology_overlay", manifest["topology_overlay"]),
        ("tp_scale_overlay", manifest["tp_scale_overlay"]),
        ("prefill_tp_size", manifest["prefill_tp_size"]),
        ("decode_tp_size", manifest["decode_tp_size"]),
        ("pd_enabled", manifest["pd_enabled"]),
        ("pd_role_layout", manifest["pd_role_layout"]),
        ("transport_mode", manifest["transport_mode"]),
        ("transport_settings_profile", manifest["transport_settings_profile"]),
        ("run_class", manifest["run_class"]),
        ("status", manifest["status"]),
        ("result_boundary", manifest["result_boundary"]),
        ("artifact_class", manifest["artifact_class"]),
        ("stop_point", manifest["stop_point"]),
        ("host", manifest["host"]),
        ("report_json", manifest["report_json"]),
    ]
    transport_pairs = list(transport_settings.items())
    path_pairs = [
        ("system_snapshot_md", system_info.get("md")),
        ("benchmark_summary_md", benchmarks.get("summary_md")),
        ("run_index_md", benchmarks.get("run_index_md")),
        ("side_by_side_md", benchmarks.get("side_by_side_md")),
    ]
    lines = [
        "# Report Manifest",
        "",
        "## Identity",
        "",
        _markdown_table_from_pairs(manifest_pairs),
        "",
        "## Transport Settings",
        "",
        _markdown_table_from_pairs(transport_pairs),
        "",
        "## Bundle Paths",
        "",
        _markdown_table_from_pairs(path_pairs, headers=("Artifact", "Path")),
    ]
    manifest_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "json": str(manifest_json_path),
        "md": str(manifest_md_path),
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
    manifest = write_bundle_manifest(
        output_root=output_root,
        report=report,
        report_path=report_path,
        system_info=system_info,
        benchmarks=benchmarks,
    )
    return {
        "manifest": manifest,
        "system_info": system_info,
        "benchmarks": benchmarks,
        "repo_state": repo_state,
        "raw_captures": raw_captures,
    }


def load_report_json(path: Path) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def find_report_jsons(root: Path) -> list[Path]:
    results = []
    for path in root.rglob("report.json"):
        if "reports" in path.parts:
            continue
        results.append(path)
    return sorted(results)


def build_rollup_rows(report_path: Path, report: dict[str, object]) -> tuple[dict[str, object], list[dict[str, object]]]:
    normalized_report = normalize_report(report)
    run_index_row = build_run_index_rows(normalized_report, report_path)[0]
    case_rows = build_case_rows(normalized_report)
    baseline_case = next(
        (
            row
            for row in case_rows
            if "myelon" not in str(row.get("execution_variant", "")).lower()
        ),
        {},
    )
    myelon_case = next(
        (
            row
            for row in case_rows
            if "myelon" in str(row.get("execution_variant", "")).lower()
        ),
        {},
    )
    side_by_side_rows = build_side_by_side_rows(normalized_report)
    metric_map = {
        row.get("metric"): row
        for row in side_by_side_rows
        if isinstance(row, dict)
    }

    def metric_row(*metric_names: str) -> dict[str, object]:
        for metric_name in metric_names:
            row = metric_map.get(metric_name)
            if isinstance(row, dict):
                return row
        return {}

    findings_row = dict(run_index_row)
    findings_row.update(
        {
            "baseline_first_prefill_seconds_mean": metric_row(
                "first_prefill_seconds_mean"
            ).get("baseline_value"),
            "myelon_first_prefill_seconds_mean": metric_row(
                "first_prefill_seconds_mean"
            ).get("myelon_value"),
            "first_prefill_seconds_delta_percent": metric_row(
                "first_prefill_seconds_mean"
            ).get("delta_percent"),
            "baseline_first_prefill_tps_mean": metric_row(
                "first_prefill_tps_mean"
            ).get("baseline_value"),
            "myelon_first_prefill_tps_mean": metric_row(
                "first_prefill_tps_mean"
            ).get("myelon_value"),
            "first_prefill_tps_delta_percent": metric_row(
                "first_prefill_tps_mean"
            ).get("delta_percent"),
            "baseline_prompt_tps_mean": metric_row(
                "prompt_tps_mean",
                "observed_prompt_tps_mean",
                "observed_prefill_tps_mean",
            ).get("baseline_value"),
            "myelon_prompt_tps_mean": metric_row(
                "prompt_tps_mean",
                "observed_prompt_tps_mean",
                "observed_prefill_tps_mean",
            ).get("myelon_value"),
            "prompt_tps_delta_percent": metric_row(
                "prompt_tps_mean",
                "observed_prompt_tps_mean",
                "observed_prefill_tps_mean",
            ).get("delta_percent"),
            "baseline_prefill_roundtrip_ms_mean": metric_row(
                "observed_prefill_roundtrip_ms_mean"
            ).get("baseline_value"),
            "myelon_prefill_roundtrip_ms_mean": metric_row(
                "observed_prefill_roundtrip_ms_mean"
            ).get("myelon_value"),
            "prefill_roundtrip_ms_delta_percent": metric_row(
                "observed_prefill_roundtrip_ms_mean"
            ).get("delta_percent"),
            "baseline_requests_per_sec": metric_map.get("requests_per_sec", {}).get("baseline_value"),
            "myelon_requests_per_sec": metric_map.get("requests_per_sec", {}).get("myelon_value"),
            "requests_per_sec_delta_percent": metric_map.get("requests_per_sec", {}).get("delta_percent"),
            "baseline_ttft_ms_mean": metric_map.get("ttft_ms_mean", {}).get("baseline_value"),
            "myelon_ttft_ms_mean": metric_map.get("ttft_ms_mean", {}).get("myelon_value"),
            "ttft_ms_delta_percent": metric_map.get("ttft_ms_mean", {}).get("delta_percent"),
            "baseline_latency_ms_mean": metric_map.get("latency_ms_mean", {}).get("baseline_value"),
            "myelon_latency_ms_mean": metric_map.get("latency_ms_mean", {}).get("myelon_value"),
            "latency_ms_delta_percent": metric_map.get("latency_ms_mean", {}).get("delta_percent"),
            "baseline_observed_gpu_kv_usage_percent_max": baseline_case.get(
                "observed_gpu_kv_usage_percent_max"
            ),
            "myelon_observed_gpu_kv_usage_percent_max": myelon_case.get(
                "observed_gpu_kv_usage_percent_max"
            ),
            "baseline_observed_cpu_swap_usage_percent_max": baseline_case.get(
                "observed_cpu_swap_usage_percent_max"
            ),
            "myelon_observed_cpu_swap_usage_percent_max": myelon_case.get(
                "observed_cpu_swap_usage_percent_max"
            ),
            "baseline_observed_successful_requests_total": baseline_case.get(
                "observed_successful_requests_total"
            ),
            "myelon_observed_successful_requests_total": myelon_case.get(
                "observed_successful_requests_total"
            ),
            "baseline_observed_failed_requests_total": baseline_case.get(
                "observed_failed_requests_total"
            ),
            "myelon_observed_failed_requests_total": myelon_case.get(
                "observed_failed_requests_total"
            ),
            "baseline_observed_http_422_rejection_count": baseline_case.get(
                "observed_http_422_rejection_count"
            ),
            "myelon_observed_http_422_rejection_count": myelon_case.get(
                "observed_http_422_rejection_count"
            ),
            "baseline_pressure_profile_outcome": baseline_case.get(
                "pressure_profile_outcome"
            ),
            "myelon_pressure_profile_outcome": myelon_case.get(
                "pressure_profile_outcome"
            ),
            "baseline_observed_cache_pressure_level": baseline_case.get(
                "observed_cache_pressure_level"
            ),
            "myelon_observed_cache_pressure_level": myelon_case.get(
                "observed_cache_pressure_level"
            ),
            "baseline_planned_max_seqs": baseline_case.get("planned_max_seqs"),
            "myelon_planned_max_seqs": myelon_case.get("planned_max_seqs"),
            "baseline_planned_usable_kvcache_tokens": baseline_case.get(
                "planned_usable_kvcache_tokens"
            ),
            "myelon_planned_usable_kvcache_tokens": myelon_case.get(
                "planned_usable_kvcache_tokens"
            ),
        }
    )
    detailed_rows: list[dict[str, object]] = []
    for row in side_by_side_rows:
        detailed_row = dict(run_index_row)
        detailed_row.update(row)
        detailed_rows.append(detailed_row)
    return findings_row, detailed_rows


def write_rollup_reports(campaign_root: Path) -> dict[str, str]:
    report_paths = find_report_jsons(campaign_root)
    reports_dir = campaign_root / "reports" / "benchmarks"
    by_family_root = reports_dir / "by_family"
    by_equivalence_root = reports_dir / "by_equivalence"
    by_workload_root = reports_dir / "by_workload"
    by_topology_root = reports_dir / "by_topology"
    by_run_class_root = reports_dir / "by_run_class"
    by_result_boundary_root = reports_dir / "by_result_boundary"
    by_artifact_class_root = reports_dir / "by_artifact_class"
    by_pressure_outcome_root = reports_dir / "by_pressure_outcome_pair"
    reports_dir.mkdir(parents=True, exist_ok=True)

    current_findings_csv = reports_dir / "current_findings.csv"
    current_findings_md = reports_dir / "current_findings.md"
    high_level_summary_md = reports_dir / "high_level_summary.md"
    rollup_run_index_csv = reports_dir / "rollup_run_index.csv"
    rollup_run_index_md = reports_dir / "rollup_run_index.md"
    per_model_side_by_side_csv = reports_dir / "per_model_side_by_side.csv"
    per_model_side_by_side_md = reports_dir / "per_model_side_by_side.md"
    all_run_commands_md = reports_dir / "all_run_commands.md"

    run_index_rows: list[dict[str, object]] = []
    findings_rows: list[dict[str, object]] = []
    detailed_rows: list[dict[str, object]] = []

    for report_path in report_paths:
        report = load_report_json(report_path)
        if not isinstance(report, dict):
            continue
        normalized_report = normalize_report(report)
        run_index_row = build_run_index_rows(normalized_report, report_path)[0]
        findings_row, detail_rows = build_rollup_rows(report_path, report)
        run_index_rows.append(run_index_row)
        findings_rows.append(findings_row)
        detailed_rows.extend(detail_rows)

    run_index_fields = (
        [key for key in run_index_rows[0].keys()]
        if run_index_rows
        else [
            "benchmark_family",
            "benchmark_submode",
            "workload_class",
            "topology_overlay",
            "transport_mode",
            "run_class",
            "status",
            "report_json",
        ]
    )
    findings_fields = (
        [key for key in findings_rows[0].keys()]
        if findings_rows
        else run_index_fields
    )
    detailed_fields = (
        [key for key in detailed_rows[0].keys()]
        if detailed_rows
        else [
            "model_label",
            "benchmark_family",
            "topology_overlay",
            "metric",
            "baseline_value",
            "myelon_value",
            "delta_percent",
        ]
    )

    _write_csv(rollup_run_index_csv, run_index_rows, run_index_fields)
    _write_csv(current_findings_csv, findings_rows, findings_fields)
    _write_csv(per_model_side_by_side_csv, detailed_rows, detailed_fields)

    status_counts: dict[str, int] = {}
    for row in findings_rows:
        key = str(row.get("status"))
        status_counts[key] = status_counts.get(key, 0) + 1
    boundary_counts: dict[str, int] = {}
    for row in findings_rows:
        key = str(row.get("result_boundary"))
        boundary_counts[key] = boundary_counts.get(key, 0) + 1
    pressure_outcome_pair_counts: dict[str, int] = {}
    for row in findings_rows:
        pair_key = row.get("pressure_profile_outcome_pair")
        if pair_key in (None, ""):
            continue
        normalized_key = str(pair_key)
        pressure_outcome_pair_counts[normalized_key] = (
            pressure_outcome_pair_counts.get(normalized_key, 0) + 1
        )

    findings_lines = [
        "# Current Findings",
        "",
        f"- campaign_root: `{campaign_root}`",
        f"- reports_found: `{len(report_paths)}`",
        "",
        "## Status Counts",
        "",
    ]
    if status_counts:
        status_rows = [{"status": key, "count": value} for key, value in sorted(status_counts.items())]
        findings_lines.append(_markdown_table_from_rows(status_rows, ["status", "count"]))
    else:
        findings_lines.append(_markdown_table_from_rows([{"status": "none", "count": 0}], ["status", "count"]))
    findings_lines.extend(
        [
            "",
            "## Boundary Counts",
            "",
        ]
    )
    if boundary_counts:
        boundary_rows = [
            {"result_boundary": key, "count": value}
            for key, value in sorted(boundary_counts.items())
        ]
        findings_lines.append(
            _markdown_table_from_rows(boundary_rows, ["result_boundary", "count"])
        )
    else:
        findings_lines.append(
            _markdown_table_from_rows(
                [{"result_boundary": "none", "count": 0}],
                ["result_boundary", "count"],
            )
        )
    findings_lines.extend(
        [
            "",
            "## Pressure Outcome Pair Counts",
            "",
        ]
    )
    if pressure_outcome_pair_counts:
        pressure_pair_rows = [
            {"pressure_profile_outcome_pair": key, "count": value}
            for key, value in sorted(pressure_outcome_pair_counts.items())
        ]
        findings_lines.append(
            _markdown_table_from_rows(
                pressure_pair_rows,
                ["pressure_profile_outcome_pair", "count"],
            )
        )
    else:
        findings_lines.append(
            _markdown_table_from_rows(
                [{"pressure_profile_outcome_pair": "none", "count": 0}],
                ["pressure_profile_outcome_pair", "count"],
            )
        )
    findings_lines.extend(
        [
            "",
            "## Campaign Findings",
            "",
        ]
    )
    if findings_rows:
        findings_lines.append(_markdown_table_from_rows(findings_rows, findings_fields))
    else:
        findings_lines.append("No retained report.json files were found.")
    current_findings_md.write_text("\n".join(findings_lines) + "\n", encoding="utf-8")

    completed_rows = [
        row
        for row in findings_rows
        if row.get("status") == "completed"
    ]
    strongest_rps = _sorted_top_rows(
        completed_rows,
        "requests_per_sec_delta_percent",
        reverse=True,
    )
    strongest_ttft = _sorted_top_rows(
        completed_rows,
        "ttft_ms_delta_percent",
        reverse=False,
    )
    strongest_prompt_tps = _sorted_top_rows(
        completed_rows,
        "prompt_tps_delta_percent",
        reverse=True,
    )
    strongest_prefill_roundtrip = _sorted_top_rows(
        completed_rows,
        "prefill_roundtrip_ms_delta_percent",
        reverse=False,
    )
    strongest_first_prefill = _sorted_top_rows(
        completed_rows,
        "first_prefill_seconds_delta_percent",
        reverse=False,
    )
    notable_regressions = _sorted_top_rows(
        completed_rows,
        "requests_per_sec_delta_percent",
        reverse=False,
    )
    incomplete_rows = [
        row
        for row in findings_rows
        if row.get("status") != "completed"
        or row.get("skip_reason")
    ]
    summary_lines = [
        "# High-Level Summary",
        "",
        f"- campaign_root: `{campaign_root}`",
        f"- reports_found: `{len(report_paths)}`",
        f"- completed_runs: `{len(completed_rows)}`",
        f"- incomplete_or_skipped_runs: `{len(incomplete_rows)}`",
        "",
        "## Pressure Outcome Pair Counts",
        "",
    ]
    if pressure_outcome_pair_counts:
        pressure_pair_rows = [
            {"pressure_profile_outcome_pair": key, "count": value}
            for key, value in sorted(pressure_outcome_pair_counts.items())
        ]
        summary_lines.append(
            _markdown_table_from_rows(
                pressure_pair_rows,
                ["pressure_profile_outcome_pair", "count"],
            )
        )
    else:
        summary_lines.append("No pressure-outcome pair data was available.")
    summary_lines.extend(
        [
            "",
        "## Strongest Requests/sec Gains",
        "",
        ]
    )
    summary_fields = [
        "model_label",
        "benchmark_family",
        "benchmark_submode",
        "topology_overlay",
        "requests_per_sec_delta_percent",
        "baseline_requests_per_sec",
        "myelon_requests_per_sec",
        "baseline_pressure_profile_outcome",
        "myelon_pressure_profile_outcome",
    ]
    if strongest_rps:
        summary_lines.append(_markdown_table_from_rows(strongest_rps, summary_fields))
    else:
        summary_lines.append("No completed baseline/Myelon comparisons were available.")
    summary_lines.extend(
        [
            "",
            "## Strongest TTFT Wins",
            "",
        ]
    )
    ttft_fields = [
        "model_label",
        "benchmark_family",
        "benchmark_submode",
        "topology_overlay",
        "ttft_ms_delta_percent",
        "baseline_ttft_ms_mean",
        "myelon_ttft_ms_mean",
        "baseline_pressure_profile_outcome",
        "myelon_pressure_profile_outcome",
    ]
    if strongest_ttft:
        summary_lines.append(_markdown_table_from_rows(strongest_ttft, ttft_fields))
    else:
        summary_lines.append("No TTFT deltas were available.")
    summary_lines.extend(
        [
            "",
            "## Strongest Prompt Throughput Gains",
            "",
        ]
    )
    prompt_fields = [
        "model_label",
        "benchmark_family",
        "benchmark_submode",
        "topology_overlay",
        "prompt_tps_delta_percent",
        "baseline_prompt_tps_mean",
        "myelon_prompt_tps_mean",
        "baseline_first_prefill_seconds_mean",
        "myelon_first_prefill_seconds_mean",
    ]
    if strongest_prompt_tps:
        summary_lines.append(_markdown_table_from_rows(strongest_prompt_tps, prompt_fields))
    else:
        summary_lines.append("No prompt-throughput deltas were available.")
    summary_lines.extend(
        [
            "",
            "## Strongest Prefill-Roundtrip Wins",
            "",
        ]
    )
    prefill_roundtrip_fields = [
        "model_label",
        "benchmark_family",
        "benchmark_submode",
        "topology_overlay",
        "prefill_roundtrip_ms_delta_percent",
        "baseline_prefill_roundtrip_ms_mean",
        "myelon_prefill_roundtrip_ms_mean",
        "baseline_pressure_profile_outcome",
        "myelon_pressure_profile_outcome",
    ]
    if strongest_prefill_roundtrip:
        summary_lines.append(
            _markdown_table_from_rows(
                strongest_prefill_roundtrip,
                prefill_roundtrip_fields,
            )
        )
    else:
        summary_lines.append("No prefill-roundtrip deltas were available.")
    summary_lines.extend(
        [
            "",
            "## Strongest First-Prefill Wins",
            "",
        ]
    )
    first_prefill_fields = [
        "model_label",
        "benchmark_family",
        "benchmark_submode",
        "topology_overlay",
        "first_prefill_seconds_delta_percent",
        "baseline_first_prefill_seconds_mean",
        "myelon_first_prefill_seconds_mean",
        "baseline_first_prefill_tps_mean",
        "myelon_first_prefill_tps_mean",
    ]
    if strongest_first_prefill:
        summary_lines.append(
            _markdown_table_from_rows(strongest_first_prefill, first_prefill_fields)
        )
    else:
        summary_lines.append("No first-prefill deltas were available.")
    summary_lines.extend(
        [
            "",
            "## Notable Regressions",
            "",
        ]
    )
    if notable_regressions:
        summary_lines.append(_markdown_table_from_rows(notable_regressions, summary_fields))
    else:
        summary_lines.append("No completed baseline/Myelon comparisons were available.")
    summary_lines.extend(
        [
            "",
            "## Incomplete / Unsupported",
            "",
        ]
    )
    incomplete_fields = [
        "model_label",
        "benchmark_family",
        "benchmark_submode",
        "topology_overlay",
        "status",
        "skip_reason",
        "report_json",
    ]
    if incomplete_rows:
        summary_lines.append(_markdown_table_from_rows(incomplete_rows, incomplete_fields))
    else:
        summary_lines.append("No incomplete or skipped runs.")
    high_level_summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    run_index_lines = [
        "# Rollup Run Index",
        "",
    ]
    if run_index_rows:
        run_index_lines.append(_markdown_table_from_rows(run_index_rows, run_index_fields))
    else:
        run_index_lines.append("No retained report.json files were found.")
    rollup_run_index_md.write_text("\n".join(run_index_lines) + "\n", encoding="utf-8")

    side_by_side_lines = [
        "# Per-Model Side By Side",
        "",
    ]
    if detailed_rows:
        side_by_side_lines.append(_markdown_table_from_rows(detailed_rows, detailed_fields))
    else:
        side_by_side_lines.append("No baseline/Myelon comparison pairs were available.")
    per_model_side_by_side_md.write_text("\n".join(side_by_side_lines) + "\n", encoding="utf-8")

    command_lines = [
        "# All Run Commands",
        "",
        f"- campaign_root: `{campaign_root}`",
        "",
    ]
    if report_paths:
        for report_path in report_paths:
            report = load_report_json(report_path)
            if not isinstance(report, dict):
                continue
            normalized_report = normalize_report(report)
            run_index_row = build_run_index_rows(normalized_report, report_path)[0]
            command_lines.extend(
                [
                    f"## {run_index_row.get('model_label')} / {run_index_row.get('benchmark_family')} / {run_index_row.get('topology_overlay')}",
                    "",
                    f"- report_json: `{report_path}`",
                    f"- status: `{run_index_row.get('status')}`",
                    f"- artifact_class: `{run_index_row.get('artifact_class')}`",
                    f"- transport_settings_profile: `{run_index_row.get('transport_settings_profile')}`",
                    "",
                ]
            )
            for case in normalized_report.get("cases", []):
                if not isinstance(case, dict):
                    continue
                command_lines.append(f"### {case.get('execution_variant', case.get('label'))}")
                command_lines.append("")
                for key in ("server_command", "pd_server_command", "client_server_command", "benchmark_command", "command"):
                    value = case.get(key)
                    if not value:
                        continue
                    if isinstance(value, list):
                        rendered = " ".join(str(item) for item in value)
                    else:
                        rendered = str(value)
                    command_lines.append(f"- {key}:")
                    command_lines.append("```bash")
                    command_lines.append(rendered)
                    command_lines.append("```")
                command_lines.append("")
    else:
        command_lines.append("No retained report.json files were found.")
    all_run_commands_md.write_text("\n".join(command_lines) + "\n", encoding="utf-8")

    grouping_specs = [
        {
            "root": by_family_root,
            "field": "benchmark_family",
            "title_prefix": "Benchmark Family",
            "findings_stem": "findings",
        },
        {
            "root": by_workload_root,
            "field": "workload_class",
            "title_prefix": "Workload Class",
            "findings_stem": "findings",
        },
        {
            "root": by_topology_root,
            "field": "topology_overlay",
            "title_prefix": "Topology Overlay",
            "findings_stem": "findings",
        },
        {
            "root": by_run_class_root,
            "field": "run_class",
            "title_prefix": "Run Class",
            "findings_stem": "findings",
        },
        {
            "root": by_result_boundary_root,
            "field": "result_boundary",
            "title_prefix": "Result Boundary",
            "findings_stem": "findings",
        },
        {
            "root": by_artifact_class_root,
            "field": "artifact_class",
            "title_prefix": "Artifact Class",
            "findings_stem": "findings",
        },
        {
            "root": by_pressure_outcome_root,
            "field": "pressure_profile_outcome_pair",
            "title_prefix": "Pressure Outcome Pair",
            "findings_stem": "findings",
        },
    ]
    for spec in grouping_specs:
        field = spec["field"]
        grouped_findings: dict[str, list[dict[str, object]]] = {}
        grouped_details: dict[str, list[dict[str, object]]] = {}
        for row in findings_rows:
            group_key = str(row.get(field) or "unspecified")
            grouped_findings.setdefault(group_key, []).append(row)
        for row in detailed_rows:
            group_key = str(row.get(field) or "unspecified")
            grouped_details.setdefault(group_key, []).append(row)
        for group_key, rows in grouped_findings.items():
            _write_grouped_report_bundle(
                group_root=spec["root"] / _slugify(group_key),
                title=f"{spec['title_prefix']}: {group_key}",
                identity_key=field,
                identity_value=group_key,
                findings_rows=rows,
                findings_fields=findings_fields,
                detailed_rows=grouped_details.get(group_key, []),
                detailed_fields=detailed_fields,
                findings_stem=spec["findings_stem"],
            )

    equivalence_groups: dict[str, list[dict[str, object]]] = {}
    equivalence_detail_groups: dict[str, list[dict[str, object]]] = {}
    for row in findings_rows:
        equivalence_key = row.get("equivalence_group")
        if equivalence_key in (None, ""):
            continue
        equivalence_groups.setdefault(str(equivalence_key), []).append(row)
    for row in detailed_rows:
        equivalence_key = row.get("equivalence_group")
        if equivalence_key in (None, ""):
            continue
        equivalence_detail_groups.setdefault(str(equivalence_key), []).append(row)
    for equivalence_key, grouped_findings in equivalence_groups.items():
        _write_grouped_report_bundle(
            group_root=by_equivalence_root / _slugify(equivalence_key),
            title=f"Matched Equivalence Group: {equivalence_key}",
            identity_key="equivalence_group",
            identity_value=equivalence_key,
            findings_rows=grouped_findings,
            findings_fields=findings_fields,
            detailed_rows=equivalence_detail_groups.get(equivalence_key, []),
            detailed_fields=detailed_fields,
            findings_stem="matched_runs",
        )

    return {
        "current_findings_csv": str(current_findings_csv),
        "current_findings_md": str(current_findings_md),
        "high_level_summary_md": str(high_level_summary_md),
        "rollup_run_index_csv": str(rollup_run_index_csv),
        "rollup_run_index_md": str(rollup_run_index_md),
        "per_model_side_by_side_csv": str(per_model_side_by_side_csv),
        "per_model_side_by_side_md": str(per_model_side_by_side_md),
        "all_run_commands_md": str(all_run_commands_md),
        "by_family_root": str(by_family_root),
        "by_equivalence_root": str(by_equivalence_root),
        "by_workload_root": str(by_workload_root),
        "by_topology_root": str(by_topology_root),
        "by_run_class_root": str(by_run_class_root),
        "by_result_boundary_root": str(by_result_boundary_root),
        "by_artifact_class_root": str(by_artifact_class_root),
        "by_pressure_outcome_root": str(by_pressure_outcome_root),
    }
