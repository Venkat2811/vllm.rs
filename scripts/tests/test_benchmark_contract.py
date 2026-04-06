import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import myelon_validation_common as validation_common
import myelon_report_common as report_common
import run_myelon_benchmark_matrix as benchmark_matrix
import run_myelon_pd_benchmark_matrix as pd_matrix
import run_myelon_server_benchmark_matrix as server_matrix


BENCHMARK_TEXT = "\n".join(
    [
        "runtime_sec = 1.23",
        "requests_per_sec = 4.56",
        "warmup_runtime_sec = 0.12",
        "total_runtime_incl_warmup_sec = 1.35",
        "[ttft_ms] avg: 12.0, min: 10.0, max: 15.0",
        "[tpot_ms] avg: 2.0, min: 1.0, max: 3.0",
        "[latency_ms] avg: 20.0, min: 18.0, max: 25.0",
    ]
)

SERVER_LOG_TEXT = "\n".join(
    [
        "2026-04-06T12:25:52.000000Z  WARN vllm_rs::utils::kvcache_allocator: KVCache Allocation: 662 GPU blocks (1.94 GB x 2), max usable kvcache tokens 42368 (48k bytes per token), scheduling limits [4 seqs x 10240 tokens]",
        "2026-04-06T12:25:53.916988Z  WARN vllm_rs::core::scheduler: Prefix cache enabled: 64 blocks (4096 tokens).",
        "2026-04-06T12:25:57.365547Z  INFO vllm_rs::core::scheduler: GPU Kvcache: 5774 blocks (369536 tokens) free, used 0.4% (0.07GB/16.99GB); CPU swap used 0.0% (0.00GB/1.70GB)",
        "2026-04-06T12:25:58.294354Z  INFO vllm_rs::core::scheduler: GPU Kvcache: 5745 blocks (367680 tokens) free, used 0.9% (0.16GB/16.99GB); CPU swap used 0.0% (0.00GB/1.70GB)",
        "2026-04-06T12:25:58.720030Z  INFO vllm_rs::core::scheduler: GPU Kvcache: 5735 blocks (367040 tokens) free, used 1.1% (0.19GB/16.99GB); CPU swap used 0.0% (0.00GB/1.70GB)",
        "2026-04-06T12:25:56.263013Z  INFO vllm_rs::core::block_manager: Prefix cache miss seq 0 (1624 tokens, 0 cached blocks, raw_match=0 blocks)",
        "2026-04-06T12:25:57.353794Z  INFO vllm_rs::core::block_manager: Prefix cache insert seq 0 (1632 tokens, 25 blocks)",
        "2026-04-06T12:25:57.403174Z  INFO vllm_rs::core::block_manager: Prefix cache miss seq 1 (1891 tokens, 25 cached blocks, raw_match=0 blocks)",
        "2026-04-06T12:25:58.282825Z  INFO vllm_rs::core::block_manager: Prefix cache insert seq 1 (1899 tokens, 29 blocks)",
    ]
)


class FakeProcess:
    def __init__(self) -> None:
        self.returncode = 0

    def poll(self) -> None:
        return None

    def send_signal(self, _signal: int) -> None:
        return None

    def wait(self, timeout: int | None = None) -> int:
        self.returncode = 0
        return 0

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = 0


def complete_run(label: str) -> dict:
    return {
        "label": label,
        "command": ["fake"],
        "exit_code": 0,
        "elapsed_seconds": 1.0,
        "metrics": {
            "response": "ok",
            "prompt_tokens": 32,
            "prompt_seconds": 0.2,
            "prompt_tokens_per_second": 160.0,
            "decoded_tokens": 16,
            "decode_seconds": 0.4,
            "decode_tokens_per_second": 40.0,
            "myelon_enabled": label.startswith("myelon"),
            "myelon_first_request_logged": label.startswith("myelon"),
            "myelon_first_response_logged": label.startswith("myelon"),
            "socket_shutdown_logged": True,
            "myelon_shutdown_logged": label.startswith("myelon"),
            "runner_prefill_error_logged": False,
            "engine_loop_error_logged": False,
            "error_logged": False,
            "runner_mode": "tp",
            "runner_reason": "test",
            "num_shards": 2,
            "device_ids": [0, 1],
        },
        "stdout": "",
        "stderr": "",
        "attempt_count": 1,
        "retried": False,
        "attempts": [],
    }


class BenchmarkContractHelperTests(unittest.TestCase):
    def test_build_benchmark_contract_requires_expected_fields(self) -> None:
        contract = validation_common.build_benchmark_contract(
            benchmark_family="prefill_stress",
            benchmark_submode="fixed_prompt_burst",
            question_answered="Does Myelon help prompt paths?",
            workload_class="synthetic_prompt_short",
            warmup_policy="cli_warmup_runs:1",
            first_turn_measured=True,
            arrival_pattern="prompt_burst_serial_runs",
            concurrency_policy={"driver": "cli", "max_num_seqs": 1},
            cache_pressure_profile="unspecified",
            equivalence_group="fixed_prompt_burst_bridge",
            topology_overlay="tp2",
            transport_mode="socket_vs_myelon_process_runner",
            run_class="quickpass",
            stop_point="full_completion",
            skip_reason=None,
        )
        self.assertEqual(contract["benchmark_family"], "prefill_stress")
        self.assertEqual(contract["benchmark_submode"], "fixed_prompt_burst")
        self.assertEqual(contract["cache_pressure_profile"], "unspecified")
        self.assertEqual(contract["equivalence_group"], "fixed_prompt_burst_bridge")
        self.assertEqual(contract["run_class"], "quickpass")
        self.assertIn("concurrency_policy", contract)

    def test_resolve_cache_pressure_profile_detects_hard_thrash(self) -> None:
        profile = validation_common.resolve_cache_pressure_profile(
            None,
            kv_fraction=0.35,
            prefix_cache_enabled=True,
            prefix_cache_max_tokens=4096,
            cpu_mem_fold=0.1,
        )
        self.assertEqual(profile, "hard_thrash")

    def test_run_class_helpers(self) -> None:
        self.assertEqual(validation_common.infer_cli_run_class(5), "fullpass")
        self.assertEqual(validation_common.infer_request_run_class(10), "quickpass")
        self.assertEqual(
            validation_common.resolve_run_class("smoke", "fullpass"),
            "smoke",
        )

    def test_model_capability_detects_pd_unsupported_hybrid_linear_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "config.json").write_text(
                json.dumps(
                    {
                        "architectures": ["Qwen3_5ForConditionalGeneration"],
                        "model_type": "qwen3_5",
                        "text_config": {
                            "layer_types": [
                                "linear_attention",
                                "full_attention",
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            capability = validation_common.classify_model_capability(tmp_path)

        self.assertEqual(capability["architecture"], "Qwen3_5ForConditionalGeneration")
        self.assertFalse(capability["pd_supported"])
        self.assertEqual(
            capability["pd_skip_reason"],
            "unsupported_architecture_pd_state_transfer",
        )

    def test_pd_topology_capability_detects_missing_visible_gpu(self) -> None:
        capability = validation_common.classify_pd_topology_capability(
            server_device_ids=[0],
            client_device_ids=[1],
            detected_cuda_device_count=1,
        )
        self.assertFalse(capability["pd_supported"])
        self.assertEqual(
            capability["pd_skip_reason"],
            "unsupported_topology_insufficient_visible_cuda_devices",
        )

    def test_pd_transport_capability_detects_missing_localipc_peer_access(self) -> None:
        with mock.patch.object(
            validation_common,
            "query_gpu_p2p_status",
            side_effect=["NS", "OK"],
        ):
            capability = validation_common.classify_pd_transport_capability(
                "pd_localipc_default",
                server_device_ids=[0],
                client_device_ids=[1],
            )

        self.assertFalse(capability["pd_supported"])
        self.assertEqual(
            capability["pd_skip_reason"],
            "unsupported_transport_localipc_missing_p2p_read",
        )

    def test_infer_model_label_handles_hf_cache_path(self) -> None:
        label = validation_common.infer_model_label(
            "/root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/abcdef"
        )
        self.assertEqual(label, "Qwen/Qwen3-4B")

    def test_extract_server_kvcache_plan_parses_scheduler_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "server.log"
            log_path.write_text(SERVER_LOG_TEXT, encoding="utf-8")

            plan = validation_common.extract_server_kvcache_plan(log_path)

        self.assertEqual(
            plan,
            {
                "planned_gpu_blocks": 662,
                "planned_usable_kvcache_tokens": 42368,
                "planned_max_seqs": 4,
                "planned_tokens_per_seq_limit": 10240,
            },
        )

    def test_infer_report_status_marks_missing_expected_cases_partial(self) -> None:
        status = report_common.infer_report_status(
            {
                "status": "completed",
                "expected_case_count": 2,
                "cases": [{"label": "runner", "benchmark_exit_code": 0}],
            }
        )
        self.assertEqual(status, "partial")

    def test_infer_case_result_boundary_classifies_completion_and_runtime(self) -> None:
        self.assertEqual(
            report_common.infer_case_result_boundary(
                {
                    "label": "runner",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                    "benchmark_exit_code": 0,
                }
            ),
            "benchmark_complete",
        )
        self.assertEqual(
            report_common.infer_case_result_boundary(
                {
                    "label": "runner",
                    "stop_point": "benchmark_timeout",
                    "skip_reason": None,
                    "benchmark_exit_code": None,
                }
            ),
            "runtime_limited",
        )
        self.assertEqual(
            report_common.infer_case_result_boundary(
                {
                    "label": "runner",
                    "stop_point": "full_completion",
                    "skip_reason": "unsupported_transport_localipc_missing_p2p_read",
                    "benchmark_exit_code": None,
                }
            ),
            "transport_limited",
        )

    def test_normalize_report_infers_result_boundary(self) -> None:
        normalized = report_common.normalize_report(
            {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "pd_qos",
                    "benchmark_submode": "cold_turn",
                    "question_answered": "pd",
                    "workload_class": "synthetic_multi_turn",
                    "warmup_policy": "measure_first_turn",
                    "first_turn_measured": True,
                    "arrival_pattern": "saturation_zero_gap",
                    "concurrency_policy": {"driver": "pd_server_client_http"},
                    "cache_pressure_profile": "unspecified",
                    "equivalence_group": None,
                    "topology_overlay": "pd_tp1",
                    "transport_mode": "pd_tcp_localhost",
                    "run_class": "fullpass",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                },
                "cases": [
                    {
                        "label": "runner_pd",
                        "stop_point": "benchmark_timeout",
                        "skip_reason": None,
                        "benchmark_exit_code": None,
                    }
                ],
            }
        )
        self.assertEqual(normalized["result_boundary"], "runtime_limited")

        skipped = report_common.normalize_report(
            {
                "status": "skipped_unsupported_architecture",
                "benchmark_contract": {
                    "benchmark_family": "pd_qos",
                    "benchmark_submode": "cold_turn",
                    "question_answered": "pd",
                    "workload_class": "synthetic_multi_turn",
                    "warmup_policy": "measure_first_turn",
                    "first_turn_measured": True,
                    "arrival_pattern": "saturation_zero_gap",
                    "concurrency_policy": {"driver": "pd_server_client_http"},
                    "cache_pressure_profile": "unspecified",
                    "equivalence_group": None,
                    "topology_overlay": "pd_tp1",
                    "transport_mode": "pd_tcp_localhost",
                    "run_class": "fullpass",
                    "stop_point": "full_completion",
                    "skip_reason": "unsupported_architecture_pd_state_transfer",
                },
                "cases": [],
            }
        )
        self.assertEqual(skipped["result_boundary"], "architecture_limited")

    def test_build_run_index_rows_include_result_boundary(self) -> None:
        report = report_common.normalize_report(
            {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "prefill_stress",
                    "benchmark_submode": "fixed_prompt_burst",
                    "question_answered": "prefill",
                    "workload_class": "synthetic_prompt_short",
                    "warmup_policy": "cli_warmup_runs:1",
                    "first_turn_measured": True,
                    "arrival_pattern": "prompt_burst_serial_runs",
                    "concurrency_policy": {"driver": "cli", "max_num_seqs": 1},
                    "cache_pressure_profile": "unspecified",
                    "equivalence_group": "fixed_prompt_burst_bridge",
                    "topology_overlay": "tp2",
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "fullpass",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                },
                "machine_profile": {"hostname": "test-host", "gpu_inventory": []},
                "model_capability": {"model_label": "Qwen/Test", "architecture": "TestArch", "pd_supported": True},
                "cases": [
                    {
                        "label": "runner",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                    }
                ],
            }
        )
        rows = report_common.build_run_index_rows(report, Path("/tmp/report.json"))
        self.assertEqual(rows[0]["result_boundary"], "benchmark_complete")

    def test_normalize_report_backfills_observed_cache_pressure_from_server_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            benchmark_log = tmp_path / "benchmark.log"
            server_log = tmp_path / "server.log"
            benchmark_log.write_text(BENCHMARK_TEXT, encoding="utf-8")
            server_log.write_text(SERVER_LOG_TEXT, encoding="utf-8")

            normalized = report_common.normalize_report(
                {
                    "benchmark_contract": {
                        "benchmark_family": "server_prefill_stress",
                        "benchmark_submode": "cache_thrash_round_robin",
                        "question_answered": "bridge",
                        "workload_class": "synthetic_server_prefill_stress",
                        "warmup_policy": "measure_first_turn",
                        "first_turn_measured": True,
                        "arrival_pattern": "saturation_zero_gap",
                        "concurrency_policy": {"driver": "persistent_http_server"},
                        "cache_pressure_profile": "hard_thrash",
                        "equivalence_group": None,
                        "topology_overlay": "tp2",
                        "transport_mode": "socket_vs_myelon_process_runner",
                        "run_class": "fullpass",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                    },
                    "cases": [
                        {
                            "label": "runner",
                            "execution_variant": "runner",
                            "benchmark_log_path": str(benchmark_log),
                            "server_log_path": str(server_log),
                        }
                    ],
                }
            )

            case = normalized["cases"][0]
            observed = case["observed_cache_pressure"]
            self.assertEqual(observed["observed_cache_pressure_level"], "minimal_pressure")
            self.assertEqual(observed["requested_cache_pressure_profile"], "hard_thrash")
            self.assertEqual(observed["pressure_profile_outcome"], "requested_thrash_not_observed")
            self.assertEqual(observed["planned_gpu_blocks"], 662)
            self.assertEqual(observed["planned_usable_kvcache_tokens"], 42368)
            self.assertEqual(observed["planned_max_seqs"], 4)
            self.assertEqual(observed["planned_tokens_per_seq_limit"], 10240)
            self.assertEqual(observed["configured_prefix_cache_blocks"], 64)
            self.assertEqual(observed["configured_prefix_cache_tokens"], 4096)
            self.assertEqual(observed["observed_prefix_cache_miss_count"], 2)
            self.assertEqual(observed["observed_prefix_cache_insert_count"], 2)
            self.assertEqual(observed["observed_prefix_cache_eviction_count"], 0)
            self.assertEqual(observed["observed_gpu_kv_usage_percent_max"], 1.1)
            self.assertEqual(observed["observed_cpu_swap_usage_percent_max"], 0.0)

            case_rows = report_common.build_case_rows(normalized)
            self.assertEqual(case_rows[0]["observed_cache_pressure_level"], "minimal_pressure")
            self.assertEqual(case_rows[0]["pressure_profile_outcome"], "requested_thrash_not_observed")
            self.assertEqual(case_rows[0]["planned_max_seqs"], 4)
            self.assertEqual(case_rows[0]["planned_usable_kvcache_tokens"], 42368)
            self.assertEqual(case_rows[0]["observed_gpu_kv_usage_percent_max"], 1.1)
            self.assertEqual(case_rows[0]["observed_cpu_swap_usage_percent_max"], 0.0)

    def test_normalize_report_classifies_requested_swap_without_cpu_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            benchmark_log = tmp_path / "benchmark.log"
            server_log = tmp_path / "server.log"
            benchmark_log.write_text(BENCHMARK_TEXT, encoding="utf-8")
            server_log.write_text(
                "\n".join(
                    [
                        "2026-04-06T12:25:52.000000Z  WARN vllm_rs::utils::kvcache_allocator: KVCache Allocation: 8192 GPU blocks (24.00 GB x 2), max usable kvcache tokens 524288 (48k bytes per token), scheduling limits [64 seqs x 8192 tokens]",
                        "2026-04-06T12:25:53.916988Z  WARN vllm_rs::core::scheduler: Prefix cache enabled: 8 blocks (512 tokens).",
                        "2026-04-06T12:25:57.365547Z  INFO vllm_rs::core::scheduler: GPU Kvcache: 345 blocks (22080 tokens) free, used 95.8% (22.99GB/24.00GB); CPU swap used 0.0% (0.00GB/48.00GB)",
                        "2026-04-06T12:25:58.720030Z  INFO vllm_rs::core::scheduler: GPU Kvcache: 221 blocks (14144 tokens) free, used 97.3% (23.35GB/24.00GB); CPU swap used 0.0% (0.00GB/48.00GB)",
                        "2026-04-06T12:25:56.263013Z  INFO vllm_rs::core::block_manager: Prefix cache miss seq 0 (6003 tokens, 8 cached blocks, raw_match=0 blocks)",
                    ]
                ),
                encoding="utf-8",
            )

            normalized = report_common.normalize_report(
                {
                    "benchmark_contract": {
                        "benchmark_family": "server_prefill_stress",
                        "benchmark_submode": "cache_thrash_round_robin",
                        "question_answered": "bridge",
                        "workload_class": "synthetic_server_prefill_stress",
                        "warmup_policy": "measure_first_turn",
                        "first_turn_measured": True,
                        "arrival_pattern": "saturation_zero_gap",
                        "concurrency_policy": {"driver": "persistent_http_server"},
                        "cache_pressure_profile": "swap_pressure",
                        "equivalence_group": None,
                        "topology_overlay": "tp2",
                        "transport_mode": "socket_vs_myelon_process_runner",
                        "run_class": "fullpass",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                    },
                    "cases": [
                        {
                            "label": "runner",
                            "execution_variant": "runner",
                            "benchmark_log_path": str(benchmark_log),
                            "server_log_path": str(server_log),
                        }
                    ],
                }
            )

            observed = normalized["cases"][0]["observed_cache_pressure"]
            self.assertEqual(observed["observed_cache_pressure_level"], "high_gpu_pressure_no_swap")
            self.assertEqual(observed["pressure_profile_outcome"], "requested_swap_reduced_to_gpu_pressure")


class BenchmarkScriptReportTests(unittest.TestCase):
    def test_server_parse_summary_extracts_prefixed_avg_lines(self) -> None:
        summary = server_matrix.parse_summary(
            "\n".join(
                [
                    "runtime_sec = 25.203",
                    "requests_per_sec = 1.270",
                    "06-04-2026 12:32:11 [INFO] - [ttft_ms                  ] avg:    340.742, min:    174.289, max:    936.404",
                    "06-04-2026 12:32:11 [INFO] - [tpot_ms                  ] avg:     12.217, min:     12.058, max:     13.709",
                    "06-04-2026 12:32:11 [INFO] - [latency_ms               ] avg:    426.262, min:    259.640, max:   1032.370",
                ]
            )
        )
        self.assertEqual(summary["requests_per_sec"], 1.270)
        self.assertEqual(summary["table"]["ttft_ms"]["mean"], 340.742)
        self.assertEqual(summary["table"]["tpot_ms"]["mean"], 12.217)
        self.assertEqual(summary["table"]["latency_ms"]["mean"], 426.262)

    def test_cli_benchmark_report_includes_contract_and_machine_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_path = tmp_path / "cli_report.json"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_OUT": str(output_path),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_BENCHMARK_MODE": "tp2",
                "VLLM_BENCHMARK_WARMUP_RUNS": "1",
                "VLLM_BENCHMARK_MEASURED_RUNS": "2",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    benchmark_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    benchmark_matrix.subprocess,
                    "run",
                    return_value=CompletedProcess(["cargo"], 0, "", ""),
                ), mock.patch.object(
                    benchmark_matrix,
                    "run_case_with_retries",
                    side_effect=[
                        complete_run("runner-warmup-1"),
                        complete_run("runner-measured-1"),
                        complete_run("runner-measured-2"),
                        complete_run("myelon-warmup-1"),
                        complete_run("myelon-measured-1"),
                        complete_run("myelon-measured-2"),
                    ],
                ):
                    rc = benchmark_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_family"], "prefill_stress")
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "fixed_prompt_burst")
            self.assertEqual(report["benchmark_contract"]["topology_overlay"], "tp2")
            self.assertEqual(report["benchmark_contract"]["run_class"], "quickpass")
            self.assertEqual(report["status"], "completed")
            self.assertIn("machine_profile", report)
            self.assertIn("model_capability", report)
            self.assertIn("report_bundle", report)
            summary_md = Path(report["report_bundle"]["benchmarks"]["summary_md"])
            details_csv = Path(report["report_bundle"]["benchmarks"]["details_csv"])
            run_index_md = Path(report["report_bundle"]["benchmarks"]["run_index_md"])
            side_by_side_md = Path(report["report_bundle"]["benchmarks"]["side_by_side_md"])
            system_md = Path(report["report_bundle"]["system_info"]["md"])
            manifest_json = Path(report["report_bundle"]["manifest"]["json"])
            self.assertTrue(summary_md.is_file())
            self.assertTrue(details_csv.is_file())
            self.assertTrue(run_index_md.is_file())
            self.assertTrue(side_by_side_md.is_file())
            self.assertTrue(system_md.is_file())
            self.assertTrue(manifest_json.is_file())

    def test_server_benchmark_report_includes_contract_and_case_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "server_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report_path = output_dir / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_family"], "serving_qos")
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "warm_steady_state")
            self.assertEqual(report["benchmark_contract"]["cache_pressure_profile"], "relaxed")
            self.assertEqual(
                report["benchmark_contract"]["transport_mode"],
                "socket_vs_myelon_process_runner",
            )
            self.assertEqual(report["benchmark_contract"]["run_class"], "quickpass")
            self.assertEqual(report["status"], "completed")
            self.assertEqual(report["expected_case_count"], 2)
            self.assertEqual(report["expected_case_labels"], ["runner", "myelon"])
            self.assertEqual(report["myelon_rpc_depth"], 8192)
            self.assertEqual(report["myelon_response_depth"], 8192)
            self.assertTrue(report["myelon_busy_spin"])
            self.assertEqual(report["cases"][0]["stop_point"], "full_completion")
            myelon_server_command = report["cases"][1]["server_command"]
            self.assertIn("--myelon-rpc-depth", myelon_server_command)
            self.assertIn("8192", myelon_server_command)
            self.assertIn("--myelon-response-depth", myelon_server_command)
            self.assertIn("--myelon-busy-spin", myelon_server_command)
            self.assertIn("machine_profile", report)
            self.assertIn("model_capability", report)
            self.assertIn("report_bundle", report)
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["details_csv"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["run_index_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["side_by_side_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["system_info"]["md"]).is_file())
            manifest_json = Path(report["report_bundle"]["manifest"]["json"])
            self.assertTrue(manifest_json.is_file())
            manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["transport_settings"]["myelon_rpc_depth"], 8192)
            self.assertTrue(manifest["transport_settings"]["myelon_busy_spin"])
            run_index_csv = Path(report["report_bundle"]["benchmarks"]["run_index_csv"])
            run_index_text = run_index_csv.read_text(encoding="utf-8")
            self.assertIn("myelon_rpc_depth", run_index_text)
            self.assertIn("myelon_response_depth", run_index_text)
            self.assertIn("myelon_busy_spin", run_index_text)

    def test_server_serving_qos_cold_turn_mode_disables_warmup_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "server_cold_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "cold_turn",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "cold_turn")
            self.assertFalse(report["warmup_step"])
            self.assertTrue(report["benchmark_contract"]["first_turn_measured"])
            self.assertEqual(report["benchmark_contract"]["warmup_policy"], "measure_first_turn")
            self.assertNotIn("--warmup-step", report["cases"][0]["benchmark_command"])

    def test_server_serving_qos_rejects_conflicting_warmup_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "server_conflict_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "cold_turn",
                "VLLM_SERVER_BENCH_WARMUP_STEP": "1",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                ) as run_mock, mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                ) as popen_mock:
                    rc = server_matrix.main()

            self.assertEqual(rc, 1)
            run_mock.assert_not_called()
            popen_mock.assert_not_called()
            self.assertFalse((output_dir / "report.json").exists())

    def test_server_serving_qos_idle_gap_mode_sets_nonzero_request_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "server_idle_gap_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "cold_turn_idle_gap",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "cold_turn_idle_gap")
            self.assertEqual(report["benchmark_contract"]["arrival_pattern"], "configured_fixed_rate")
            self.assertEqual(report["benchmark_contract"]["warmup_policy"], "measure_first_turn")
            self.assertEqual(report["request_rate"], 1.0)
            self.assertFalse(report["warmup_step"])

    def test_server_prefill_stress_report_includes_cache_pressure_profile_and_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "server_prefill_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "cache_thrash_round_robin",
                "VLLM_SERVER_PREFIX_CACHE": "1",
                "VLLM_SERVER_PREFIX_CACHE_MAX_TOKENS": "4096",
                "VLLM_SERVER_KV_FRACTION": "0.35",
                "VLLM_SERVER_CPU_MEM_FOLD": "0.1",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report_path = output_dir / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(
                report["benchmark_contract"]["benchmark_family"],
                "server_prefill_stress",
            )
            self.assertEqual(
                report["benchmark_contract"]["benchmark_submode"],
                "cache_thrash_round_robin",
            )
            self.assertEqual(
                report["benchmark_contract"]["cache_pressure_profile"],
                "hard_thrash",
            )
            self.assertTrue(report["prefix_cache_enabled"])
            self.assertEqual(report["prefix_cache_max_tokens"], 4096)
            self.assertEqual(report["kv_fraction"], 0.35)
            self.assertEqual(report["cpu_mem_fold"], 0.1)
            runner_command = report["cases"][0]["server_command"]
            self.assertIn("--prefix-cache", runner_command)
            self.assertIn("--prefix-cache-max-tokens", runner_command)
            self.assertIn("--kv-fraction", runner_command)
            self.assertIn("--cpu-mem-fold", runner_command)
            self.assertNotIn("--max-model-len", runner_command)

    def test_server_prefill_stress_defaults_to_round_robin_low_decode_and_builtin_workload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_default_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_family"], "server_prefill_stress")
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "cache_thrash_round_robin")
            self.assertEqual(report["benchmark_contract"]["cache_pressure_profile"], "hard_thrash")
            self.assertFalse(report["warmup_step"])
            self.assertEqual(report["max_num_seqs"], 64)
            self.assertEqual(report["num_clients"], 32)
            self.assertEqual(report["max_num_requests"], 384)
            self.assertEqual(report["conversation_sampling"], "round_robin")
            self.assertEqual(report["limit_min_tokens"], 8)
            self.assertEqual(report["limit_max_tokens"], 8)
            self.assertTrue(report["workload_file"].endswith("synthetic_server_prefill_stress_round_robin.json"))
            benchmark_command = report["cases"][0]["benchmark_command"]
            self.assertIn("--num-clients", benchmark_command)
            self.assertIn("32", benchmark_command)
            self.assertIn("--conversation-sampling", benchmark_command)
            self.assertIn("--max-num-requests", benchmark_command)
            self.assertIn("384", benchmark_command)
            self.assertIn("--limit-min-tokens", benchmark_command)
            self.assertIn("--limit-max-tokens", benchmark_command)
            self.assertNotIn("--warmup-step", benchmark_command)
            run_index_csv = Path(report["report_bundle"]["benchmarks"]["run_index_csv"])
            run_index_text = run_index_csv.read_text(encoding="utf-8")
            self.assertIn("conversation_sampling", run_index_text)
            self.assertIn("round_robin", run_index_text)
            self.assertIn("limit_min_tokens", run_index_text)
            self.assertIn("limit_max_tokens", run_index_text)
            self.assertIn("prefix_cache_max_tokens", run_index_text)
            self.assertIn("kv_fraction", run_index_text)
            self.assertIn("cpu_mem_fold", run_index_text)
            server_command = report["cases"][0]["server_command"]
            self.assertIn("--max-num-seqs", server_command)
            self.assertIn("64", server_command)
            self.assertIn("--prefix-cache", server_command)
            self.assertIn("--prefix-cache-max-tokens", server_command)
            self.assertIn("--kv-fraction", server_command)
            self.assertIn("--cpu-mem-fold", server_command)
            self.assertNotIn("--max-model-len", server_command)

    def test_server_prefill_shared_prefix_control_selects_builtin_workload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_shared_prefix_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "shared_prefix_round_robin_control",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(
                report["benchmark_contract"]["benchmark_submode"],
                "shared_prefix_round_robin_control",
            )
            self.assertEqual(report["benchmark_contract"]["cache_pressure_profile"], "bounded_prefix")
            self.assertEqual(report["num_clients"], 32)
            self.assertEqual(report["max_num_requests"], 384)
            self.assertTrue(
                report["workload_file"].endswith(
                    "synthetic_server_prefill_shared_prefix_round_robin.json"
                )
            )

    def test_server_prefill_round_robin_inputs_repeat_source_text(self) -> None:
        inputs_dir = (
            SCRIPTS_DIR.parent
            / "artifacts"
            / "h100_benchmarking_2026_04_06"
            / "inputs"
        )
        long_source_path = inputs_dir / "synthetic_server_prefill_long_source.txt"
        self.assertTrue(long_source_path.is_file())
        self.assertGreater(
            long_source_path.stat().st_size,
            1_000_000,
            msg="synthetic_server_prefill_long_source.txt should be large enough for heavy round-robin prompts",
        )
        for name in (
            "synthetic_server_prefill_stress_round_robin.json",
            "synthetic_server_prefill_shared_prefix_round_robin.json",
        ):
            payload = json.loads((inputs_dir / name).read_text(encoding="utf-8"))
            self.assertEqual(
                payload["num_conversations"],
                64,
                msg=f"{name} should keep enough conversations to create real reuse distance",
            )
            self.assertGreaterEqual(
                len(payload["text_files"]),
                1,
                msg=f"{name} should reference at least one large source text file",
            )
            self.assertTrue(
                all(
                    path.endswith("synthetic_server_prefill_long_source.txt")
                    for path in payload["text_files"]
                ),
                msg=f"{name} should use the dedicated long source text for heavy round-robin generation",
            )
            self.assertEqual(
                payload["prompt_output"]["num_tokens"]["value"],
                8,
                msg=f"{name} should remain low-decode",
            )

    def test_server_prefill_low_decode_selects_builtin_workload_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_low_decode_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "low_decode",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "low_decode")
            self.assertEqual(report["benchmark_contract"]["cache_pressure_profile"], "relaxed")
            self.assertEqual(report["num_clients"], 16)
            self.assertEqual(report["max_active_conversations"], 32)
            self.assertEqual(report["max_num_requests"], 192)
            self.assertEqual(report["limit_min_tokens"], 16)
            self.assertEqual(report["limit_max_tokens"], 32)
            self.assertTrue(
                report["workload_file"].endswith(
                    "synthetic_server_prefill_stress_round_robin.json"
                )
            )

    def test_server_prefill_fixed_prompt_burst_selects_builtin_workload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_fixed_prompt_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "fixed_prompt_burst",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(
                report["benchmark_contract"]["benchmark_submode"],
                "fixed_prompt_burst",
            )
            self.assertEqual(report["benchmark_contract"]["cache_pressure_profile"], "relaxed")
            self.assertEqual(
                report["benchmark_contract"]["equivalence_group"],
                "fixed_prompt_burst_bridge",
            )
            self.assertEqual(report["max_num_seqs"], 32)
            self.assertTrue(
                report["workload_file"].endswith(
                    "synthetic_server_prefill_fixed_prompt_burst.json"
                )
            )
            self.assertEqual(report["limit_min_tokens"], 1)
            self.assertEqual(report["limit_max_tokens"], 1)
            self.assertFalse(report["prefix_cache_enabled"])
            server_command = report["cases"][0]["server_command"]
            self.assertIn("--max-num-seqs", server_command)
            self.assertIn("32", server_command)
            self.assertIn("--kv-fraction", server_command)
            self.assertNotIn("--max-model-len", server_command)
            benchmark_command = report["cases"][0]["benchmark_command"]
            self.assertIn("benchmark_server_fixed_prompt_burst.py", " ".join(benchmark_command))
            self.assertIn("--prompt-text", benchmark_command)
            self.assertIn("Please talk about China in more details.", benchmark_command)
            self.assertNotIn("--input-file", benchmark_command)

    def test_server_prefill_stress_tracks_active_conversation_override_for_seq_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_override_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "fixed_prompt_burst",
                "VLLM_SERVER_BENCH_MAX_ACTIVE_CONVERSATIONS": "256",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "256",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["max_active_conversations"], 256)
            self.assertEqual(report["max_num_requests"], 256)
            self.assertEqual(report["max_num_seqs"], 256)
            server_command = report["cases"][0]["server_command"]
            self.assertIn("--max-num-seqs", server_command)
            self.assertIn("256", server_command)

    def test_server_prefill_explicit_max_model_len_drops_default_kv_fraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_explicit_len_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "fixed_prompt_burst",
                "VLLM_MAX_MODEL_LEN": "2560",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["max_model_len"], 2560)
            self.assertIsNone(report["kv_fraction"])
            server_command = report["cases"][0]["server_command"]
            self.assertIn("--max-model-len", server_command)
            self.assertIn("2560", server_command)
            self.assertNotIn("--kv-fraction", server_command)

    def test_server_prefill_rejects_explicit_max_model_len_with_explicit_kv_fraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_conflict_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_MAX_MODEL_LEN": "2560",
                "VLLM_SERVER_KV_FRACTION": "0.35",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                ) as run_mock, mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                ) as popen_mock:
                    rc = server_matrix.main()

            self.assertEqual(rc, 1)
            run_mock.assert_not_called()
            popen_mock.assert_not_called()
            self.assertFalse((output_dir / "report.json").exists())

    def test_server_prefill_swap_pressure_with_explicit_max_model_len_keeps_supported_profile_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_swap_profile_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "cache_thrash_round_robin",
                "VLLM_CACHE_PRESSURE_PROFILE": "swap_pressure",
                "VLLM_MAX_MODEL_LEN": "8192",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["max_model_len"], 8192)
            self.assertEqual(report["cache_pressure_profile"], "swap_pressure")
            self.assertIsNone(report["kv_fraction"])
            self.assertEqual(report["cpu_mem_fold"], 2.0)
            self.assertEqual(report["prefix_cache_max_tokens"], 512)
            self.assertEqual(report["limit_min_tokens"], 32)
            self.assertEqual(report["limit_max_tokens"], 32)
            server_command = report["cases"][0]["server_command"]
            self.assertIn("--max-model-len", server_command)
            self.assertIn("8192", server_command)
            self.assertNotIn("--kv-fraction", server_command)
            self.assertIn("--cpu-mem-fold", server_command)
            self.assertIn("2.0", server_command)

    def test_server_prefill_swap_pressure_stops_when_allocator_collapses_seq_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_dir = tmp_path / "server_prefill_swap_collapse_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "single_gpu",
                "VLLM_SERVER_BENCHMARK_FAMILY": "server_prefill_stress",
                "VLLM_SERVER_BENCHMARK_SUBMODE": "cache_thrash_round_robin",
                "VLLM_CACHE_PRESSURE_PROFILE": "swap_pressure",
                "VLLM_SERVER_KV_FRACTION": "0.08",
                "VLLM_SERVER_CPU_MEM_FOLD": "2.0",
                "VLLM_SERVER_PREFIX_CACHE_MAX_TOKENS": "512",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] in {"cargo", "nvidia-smi", "git"}:
                    return CompletedProcess(command, 0, "", "")
                raise AssertionError("benchmark command should not execute after allocator collapse")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    server_matrix,
                    "validate_requested_topology",
                    return_value=2,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    server_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    server_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    server_matrix,
                    "extract_server_kvcache_plan",
                    return_value={
                        "planned_gpu_blocks": 662,
                        "planned_usable_kvcache_tokens": 42368,
                        "planned_max_seqs": 1,
                        "planned_tokens_per_seq_limit": 40960,
                    },
                ), mock.patch.object(
                    server_matrix,
                    "terminate_process",
                    return_value=0,
                ):
                    rc = server_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "partial")
            self.assertEqual(
                report["cases"][0]["stop_point"],
                "allocator_seq_capacity_collapse",
            )
            self.assertEqual(
                report["cases"][0]["skip_reason"],
                "swap_pressure_profile_collapsed_effective_seq_capacity",
            )
            self.assertIsNone(report["cases"][0].get("benchmark_exit_code"))
            self.assertEqual(
                report["cases"][0]["allocator_plan"]["planned_max_seqs"],
                1,
            )
            benchmark_log_text = Path(
                report["cases"][0]["benchmark_log_path"]
            ).read_text(encoding="utf-8")
            self.assertIn("collapsed effective server capacity to 1 seq", benchmark_log_text)

    def test_pd_benchmark_report_includes_contract_and_case_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "pd_transfer_first_request.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0",
                "VLLM_PD_CLIENT_DEVICE_IDS": "1",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    pd_matrix,
                    "validate_device_roles",
                    return_value=None,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    pd_matrix,
                    "wait_for_pd_server_ready",
                    return_value=None,
                ), mock.patch.object(
                    pd_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    pd_matrix,
                    "classify_pd_transport_capability",
                    return_value={
                        "transport_mode": "pd_localipc_default",
                        "server_device_ids": [0],
                        "client_device_ids": [1],
                        "peer_read_status": "OK",
                        "peer_write_status": "OK",
                        "pd_supported": True,
                        "pd_skip_reason": None,
                    },
                ), mock.patch.object(
                    pd_matrix,
                    "terminate_process",
                    return_value=0,
                ), mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=2,
                ):
                    rc = pd_matrix.main()

            self.assertEqual(rc, 0)
            report_path = output_dir / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_family"], "pd_qos")
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "first_transfer_control")
            self.assertEqual(report["benchmark_contract"]["transport_mode"], "pd_localipc_default")
            self.assertEqual(report["benchmark_contract"]["run_class"], "quickpass")
            self.assertEqual(report["status"], "completed")
            self.assertEqual(report["expected_case_count"], 2)
            self.assertEqual(report["expected_case_labels"], ["runner_pd", "myelon_pd"])
            self.assertEqual(report["myelon_rpc_depth"], 8192)
            self.assertEqual(report["myelon_response_depth"], 8192)
            self.assertTrue(report["myelon_busy_spin"])
            self.assertEqual(report["cases"][0]["stop_point"], "full_completion")
            myelon_case = report["cases"][1]
            self.assertIn("--myelon-rpc-depth", myelon_case["pd_server_command"])
            self.assertIn("--myelon-response-depth", myelon_case["pd_server_command"])
            self.assertIn("--myelon-busy-spin", myelon_case["pd_server_command"])
            self.assertIn("--myelon-rpc-depth", myelon_case["client_server_command"])
            self.assertIn("--myelon-response-depth", myelon_case["client_server_command"])
            self.assertIn("--myelon-busy-spin", myelon_case["client_server_command"])
            self.assertIn("machine_profile", report)
            self.assertIn("model_capability", report)
            self.assertIn("topology_capability", report)
            self.assertIn("report_bundle", report)
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["details_csv"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["run_index_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["side_by_side_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["system_info"]["md"]).is_file())

    def test_pd_cold_turn_mode_disables_warmup_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_cold_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0",
                "VLLM_PD_CLIENT_DEVICE_IDS": "1",
                "VLLM_PD_BENCHMARK_SUBMODE": "cold_turn",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    pd_matrix,
                    "validate_device_roles",
                    return_value=None,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    pd_matrix,
                    "wait_for_pd_server_ready",
                    return_value=None,
                ), mock.patch.object(
                    pd_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    pd_matrix,
                    "classify_pd_transport_capability",
                    return_value={
                        "transport_mode": "pd_localipc_default",
                        "server_device_ids": [0],
                        "client_device_ids": [1],
                        "peer_read_status": "OK",
                        "peer_write_status": "OK",
                        "pd_supported": True,
                        "pd_skip_reason": None,
                    },
                ), mock.patch.object(
                    pd_matrix,
                    "terminate_process",
                    return_value=0,
                ), mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=2,
                ):
                    rc = pd_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "cold_turn")
            self.assertFalse(report["warmup_step"])
            self.assertTrue(report["benchmark_contract"]["first_turn_measured"])
            self.assertNotIn("--warmup-step", report["cases"][0]["benchmark_command"])

    def test_pd_rejects_conflicting_warmup_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_conflict_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0",
                "VLLM_PD_CLIENT_DEVICE_IDS": "1",
                "VLLM_PD_BENCHMARK_SUBMODE": "cold_turn",
                "VLLM_SERVER_BENCH_WARMUP_STEP": "1",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    pd_matrix,
                    "classify_pd_transport_capability",
                    return_value={
                        "transport_mode": "pd_localipc_default",
                        "server_device_ids": [0],
                        "client_device_ids": [1],
                        "peer_read_status": "OK",
                        "peer_write_status": "OK",
                        "pd_supported": True,
                        "pd_skip_reason": None,
                    },
                ), mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=2,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "run",
                ) as run_mock, mock.patch.object(
                    pd_matrix.subprocess,
                    "Popen",
                ) as popen_mock:
                    rc = pd_matrix.main()

            self.assertEqual(rc, 1)
            run_mock.assert_not_called()
            popen_mock.assert_not_called()
            self.assertFalse((output_dir / "report.json").exists())

    def test_pd_idle_gap_mode_sets_nonzero_request_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_idle_gap_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0",
                "VLLM_PD_CLIENT_DEVICE_IDS": "1",
                "VLLM_PD_BENCHMARK_SUBMODE": "cold_turn_idle_gap",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            def fake_run(*args, **kwargs):
                command = args[0]
                if command[0] == "cargo":
                    return CompletedProcess(command, 0, "", "")
                return CompletedProcess(command, 0, BENCHMARK_TEXT, "")

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    pd_matrix,
                    "validate_device_roles",
                    return_value=None,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "run",
                    side_effect=fake_run,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ), mock.patch.object(
                    pd_matrix,
                    "wait_for_pd_server_ready",
                    return_value=None,
                ), mock.patch.object(
                    pd_matrix,
                    "wait_for_server_ready",
                    return_value={"data": [{"id": "served-model"}]},
                ), mock.patch.object(
                    pd_matrix,
                    "classify_pd_transport_capability",
                    return_value={
                        "transport_mode": "pd_localipc_default",
                        "server_device_ids": [0],
                        "client_device_ids": [1],
                        "peer_read_status": "OK",
                        "peer_write_status": "OK",
                        "pd_supported": True,
                        "pd_skip_reason": None,
                    },
                ), mock.patch.object(
                    pd_matrix,
                    "terminate_process",
                    return_value=0,
                ), mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=2,
                ):
                    rc = pd_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["benchmark_submode"], "cold_turn_idle_gap")
            self.assertEqual(report["benchmark_contract"]["arrival_pattern"], "configured_fixed_rate")
            self.assertEqual(report["benchmark_contract"]["warmup_policy"], "measure_first_turn")
            self.assertEqual(report["request_rate"], 1.0)
            self.assertFalse(report["warmup_step"])

    def test_pd_benchmark_unsupported_model_writes_skip_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            (model_dir / "config.json").write_text(
                json.dumps(
                    {
                        "architectures": ["Qwen3_5ForConditionalGeneration"],
                        "model_type": "qwen3_5",
                        "text_config": {"layer_types": ["linear_attention", "full_attention"]},
                    }
                ),
                encoding="utf-8",
            )
            workload_file = tmp_path / "pd_transfer_first_request.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_skip_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0",
                "VLLM_PD_CLIENT_DEVICE_IDS": "1",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    pd_matrix,
                    "validate_device_roles",
                    return_value=None,
                ), mock.patch.object(
                    pd_matrix.subprocess,
                    "run",
                ) as mocked_run, mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=2,
                    ):
                    rc = pd_matrix.main()

            self.assertEqual(rc, 0)
            cargo_build_calls = [
                call_args
                for call_args in mocked_run.call_args_list
                if call_args.args
                and call_args.args[0]
                and call_args.args[0][0:2] == ["cargo", "build"]
            ]
            self.assertEqual(cargo_build_calls, [])
            report_path = output_dir / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "skipped_unsupported_architecture")
            self.assertEqual(
                report["benchmark_contract"]["skip_reason"],
                "unsupported_architecture_pd_state_transfer",
            )
            self.assertFalse(report["model_capability"]["pd_supported"])
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["run_index_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["side_by_side_md"]).is_file())

    def test_pd_benchmark_unsupported_topology_writes_skip_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            (model_dir / "config.json").write_text(
                json.dumps(
                    {
                        "architectures": ["Qwen3ForCausalLM"],
                        "model_type": "qwen3",
                    }
                ),
                encoding="utf-8",
            )
            workload_file = tmp_path / "pd_transfer_first_request.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_topology_skip_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0",
                "VLLM_PD_CLIENT_DEVICE_IDS": "1",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    pd_matrix.subprocess,
                    "run",
                ) as mocked_run, mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=1,
                ):
                    rc = pd_matrix.main()

            self.assertEqual(rc, 0)
            cargo_build_calls = [
                call_args
                for call_args in mocked_run.call_args_list
                if call_args.args
                and call_args.args[0]
                and call_args.args[0][0:2] == ["cargo", "build"]
            ]
            self.assertEqual(cargo_build_calls, [])
            report_path = output_dir / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "skipped_unsupported_topology")
            self.assertEqual(
                report["benchmark_contract"]["skip_reason"],
                "unsupported_topology_insufficient_visible_cuda_devices",
            )
            self.assertFalse(report["topology_capability"]["pd_supported"])
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())

    def test_pd_benchmark_unsupported_transport_writes_skip_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            (model_dir / "config.json").write_text(
                json.dumps(
                    {
                        "architectures": ["Qwen3ForCausalLM"],
                        "model_type": "qwen3",
                    }
                ),
                encoding="utf-8",
            )
            workload_file = tmp_path / "pd_transfer_first_request.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_transport_skip_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0",
                "VLLM_PD_CLIENT_DEVICE_IDS": "1",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
                "VLLM_RUN_CLASS": "quickpass",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    pd_matrix.subprocess,
                    "run",
                ) as mocked_run, mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=2,
                ), mock.patch.object(
                    pd_matrix,
                    "classify_pd_transport_capability",
                    return_value={
                        "transport_mode": "pd_localipc_default",
                        "server_device_ids": [0],
                        "client_device_ids": [1],
                        "peer_read_status": "NS",
                        "peer_write_status": "OK",
                        "pd_supported": False,
                        "pd_skip_reason": "unsupported_transport_localipc_missing_p2p_read",
                    },
                ):
                    rc = pd_matrix.main()

            self.assertEqual(rc, 0)
            cargo_build_calls = [
                call_args
                for call_args in mocked_run.call_args_list
                if call_args.args
                and call_args.args[0]
                and call_args.args[0][0:2] == ["cargo", "build"]
            ]
            self.assertEqual(cargo_build_calls, [])
            report_path = output_dir / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "skipped_unsupported_transport")
            self.assertEqual(
                report["benchmark_contract"]["skip_reason"],
                "unsupported_transport_localipc_missing_p2p_read",
            )
            self.assertFalse(report["transport_capability"]["pd_supported"])
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())

    def test_rollup_reports_aggregate_retained_campaigns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            campaign_a = tmp_path / "single_gpu_random_qwen3_4b"
            campaign_b = tmp_path / "pd_skip_qwen35_27b"
            campaign_a.mkdir()
            campaign_b.mkdir()

            report_a = {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "serving_qos",
                    "benchmark_submode": "warm_steady_state",
                    "workload_class": "synthetic_multi_turn",
                    "topology_overlay": "single_gpu",
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "quickpass",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                },
                "machine_profile": {
                    "hostname": "plain-bear-unfolds-fin-02",
                    "gpu_inventory": [{"name": "NVIDIA H100 80GB HBM3"}],
                },
                "model_capability": {
                    "model_label": "Qwen/Qwen3-4B",
                    "architecture": "Qwen3ForCausalLM",
                    "pd_supported": True,
                },
                "cases": [
                    {
                        "label": "runner",
                        "execution_variant": "runner",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "summary": {
                            "requests_per_sec": 3.0,
                            "runtime_sec": 1.1,
                            "table": {
                                "ttft_ms": {"mean": 90.0},
                                "tpot_ms": {"mean": 8.0},
                                "latency_ms": {"mean": 320.0},
                            },
                        },
                    },
                    {
                        "label": "myelon",
                        "execution_variant": "myelon",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "summary": {
                            "requests_per_sec": 3.2,
                            "runtime_sec": 1.0,
                            "table": {
                                "ttft_ms": {"mean": 80.0},
                                "tpot_ms": {"mean": 7.5},
                                "latency_ms": {"mean": 300.0},
                            },
                        },
                    },
                ],
            }
            report_b = {
                "status": "skipped_unsupported_topology",
                "benchmark_contract": {
                    "benchmark_family": "pd_qos",
                    "benchmark_submode": "first_transfer_control",
                    "workload_class": "pd_first_transfer_control",
                    "topology_overlay": "pd_tp1",
                    "transport_mode": "pd_localipc_default",
                    "run_class": "quickpass",
                    "stop_point": "full_completion",
                    "skip_reason": "unsupported_topology_insufficient_visible_cuda_devices",
                },
                "machine_profile": {
                    "hostname": "plain-bear-unfolds-fin-02",
                    "gpu_inventory": [{"name": "NVIDIA H100 80GB HBM3"}],
                },
                "model_capability": {
                    "model_label": "Qwen/Qwen3.5-27B-FP8",
                    "architecture": "Qwen3_5ForConditionalGeneration",
                    "pd_supported": False,
                },
                "cases": [],
            }
            (campaign_a / "report.json").write_text(json.dumps(report_a), encoding="utf-8")
            (campaign_b / "report.json").write_text(json.dumps(report_b), encoding="utf-8")

            outputs = report_common.write_rollup_reports(tmp_path)

            current_findings_md = Path(outputs["current_findings_md"])
            high_level_summary_md = Path(outputs["high_level_summary_md"])
            rollup_run_index_md = Path(outputs["rollup_run_index_md"])
            per_model_side_by_side_md = Path(outputs["per_model_side_by_side_md"])
            all_run_commands_md = Path(outputs["all_run_commands_md"])
            self.assertTrue(current_findings_md.is_file())
            self.assertTrue(high_level_summary_md.is_file())
            self.assertTrue(rollup_run_index_md.is_file())
            self.assertTrue(per_model_side_by_side_md.is_file())
            self.assertTrue(all_run_commands_md.is_file())

            findings_text = current_findings_md.read_text(encoding="utf-8")
            self.assertIn("Qwen/Qwen3-4B", findings_text)
            self.assertIn("skipped_unsupported_topology", findings_text)

            high_level_text = high_level_summary_md.read_text(encoding="utf-8")
            self.assertIn("Strongest Requests/sec Gains", high_level_text)
            self.assertIn("Incomplete / Unsupported", high_level_text)

            side_text = per_model_side_by_side_md.read_text(encoding="utf-8")
            self.assertIn("requests_per_sec", side_text)
            self.assertIn("Qwen/Qwen3-4B", side_text)

            commands_text = all_run_commands_md.read_text(encoding="utf-8")
            self.assertIn("All Run Commands", commands_text)

    def test_normalize_report_backfills_summary_means_from_benchmark_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            benchmark_log_path = tmp_path / "benchmark.log"
            benchmark_log_path.write_text(
                "\n".join(
                    [
                        "runtime_sec = 25.203",
                        "requests_per_sec = 1.270",
                        "06-04-2026 12:32:11 [INFO] - [ttft_ms                  ] avg:    340.742, min:    174.289, max:    936.404",
                        "06-04-2026 12:32:11 [INFO] - [tpot_ms                  ] avg:     12.217, min:     12.058, max:     13.709",
                        "06-04-2026 12:32:11 [INFO] - [latency_ms               ] avg:    426.262, min:    259.640, max:   1032.370",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "server_prefill_stress",
                    "benchmark_submode": "shared_prefix_round_robin_control",
                    "workload_class": "synthetic_server_shared_prefix_control",
                    "topology_overlay": "tp2",
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "fullpass",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                },
                "machine_profile": {
                    "hostname": "plain-bear-unfolds-fin-02",
                    "gpu_inventory": [{"name": "NVIDIA H100 80GB HBM3"}],
                },
                "model_capability": {
                    "model_label": "Qwen/Qwen3-30B-A3B",
                    "architecture": "Qwen3MoeForCausalLM",
                    "pd_supported": True,
                },
                "cases": [
                    {
                        "label": "runner",
                        "execution_variant": "runner",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "benchmark_log_path": str(benchmark_log_path),
                        "summary": {
                            "requests_per_sec": 1.27,
                            "runtime_sec": 25.203,
                            "table": {},
                        },
                    }
                ],
            }

            normalized = report_common.normalize_report(report)
            case_rows = report_common.build_case_rows(normalized)

            self.assertEqual(case_rows[0]["requests_per_sec"], 1.27)
            self.assertEqual(case_rows[0]["runtime_sec"], 25.203)
            self.assertAlmostEqual(case_rows[0]["ttft_ms_mean"], 340.742)
            self.assertAlmostEqual(case_rows[0]["tpot_ms_mean"], 12.217)
            self.assertAlmostEqual(case_rows[0]["latency_ms_mean"], 426.262)

    def test_normalize_report_backfills_truncated_summary_rows_from_benchmark_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            benchmark_log_path = tmp_path / "benchmark.log"
            benchmark_log_path.write_text(
                "\n".join(
                    [
                        "runtime_sec = 25.472",
                        "requests_per_sec = 1.256",
                        "                   count     mean     std  ...      75%      90%      max",
                        "ttft_ms             32.0   703.48  324.80  ...   939.36  1061.53  1383.45",
                        "tpot_ms             32.0    12.25    0.31  ...    12.22    12.29    13.91",
                        "latency_ms          32.0   789.25  325.44  ...  1025.09  1157.72  1469.14",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "server_prefill_stress",
                    "benchmark_submode": "cache_thrash_round_robin",
                    "workload_class": "synthetic_server_prefill_stress",
                    "topology_overlay": "tp2",
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "fullpass",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                },
                "machine_profile": {
                    "hostname": "plain-bear-unfolds-fin-02",
                    "gpu_inventory": [{"name": "NVIDIA H100 80GB HBM3"}],
                },
                "model_capability": {
                    "model_label": "Qwen/Qwen3-30B-A3B",
                    "architecture": "Qwen3MoeForCausalLM",
                    "pd_supported": True,
                },
                "cases": [
                    {
                        "label": "runner",
                        "execution_variant": "runner",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "benchmark_log_path": str(benchmark_log_path),
                        "summary": {
                            "requests_per_sec": 1.256,
                            "runtime_sec": 25.472,
                            "table": {},
                        },
                    }
                ],
            }

            normalized = report_common.normalize_report(report)
            case_rows = report_common.build_case_rows(normalized)

            self.assertEqual(case_rows[0]["requests_per_sec"], 1.256)
            self.assertEqual(case_rows[0]["runtime_sec"], 25.472)
            self.assertAlmostEqual(case_rows[0]["ttft_ms_mean"], 703.48)
            self.assertAlmostEqual(case_rows[0]["tpot_ms_mean"], 12.25)
            self.assertAlmostEqual(case_rows[0]["latency_ms_mean"], 789.25)

    def test_normalize_report_backfills_benchmark_outcome_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            runner_log_path = tmp_path / "runner_benchmark.log"
            myelon_log_path = tmp_path / "myelon_benchmark.log"
            runner_log_path.write_text(
                "\n".join(
                    [
                        "runtime_sec = 10.0",
                        "requests_per_sec = 3.0",
                        "06-04-2026 15:29:09 [INFO] - Client 1 has no more work",
                        "06-04-2026 15:29:09 [INFO] - Client 1 is done (num_successes=5, num_failures=0)",
                        "06-04-2026 15:29:09 [INFO] - Sending termination signal to clients",
                        "06-04-2026 15:29:09 [INFO] - Client 2 received a termination signal",
                        "06-04-2026 15:29:09 [INFO] - Client 2 is done (num_successes=4, num_failures=0)",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            myelon_log_path.write_text(
                "\n".join(
                    [
                        "runtime_sec = 11.0",
                        "requests_per_sec = 2.5",
                        '06-04-2026 15:26:27 [WARNING] - Received HTTP status 422 (Unprocessable Entity): {"message":"Stream generation failed"}',
                        "06-04-2026 15:26:27 [INFO] - Client 3 has no more work",
                        "06-04-2026 15:26:27 [INFO] - Client 3 is done (num_successes=1, num_failures=1)",
                        "06-04-2026 15:26:27 [INFO] - Sending termination signal to clients",
                        "06-04-2026 15:26:27 [INFO] - Client 4 received a termination signal",
                        "06-04-2026 15:26:27 [INFO] - Client 4 is done (num_successes=2, num_failures=0)",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "server_prefill_stress",
                    "benchmark_submode": "cache_thrash_round_robin",
                    "workload_class": "synthetic_server_prefill_stress",
                    "topology_overlay": "tp2",
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "fullpass",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                },
                "machine_profile": {
                    "hostname": "hazy-instance-completes-fin-02",
                    "gpu_inventory": [{"name": "NVIDIA H100 80GB HBM3"}],
                },
                "model_capability": {
                    "model_label": "Qwen/Qwen3-0.6B",
                    "architecture": "Qwen3ForCausalLM",
                    "pd_supported": True,
                },
                "cases": [
                    {
                        "label": "runner",
                        "execution_variant": "runner",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "benchmark_log_path": str(runner_log_path),
                        "summary": {"table": {}},
                    },
                    {
                        "label": "myelon",
                        "execution_variant": "myelon",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "benchmark_log_path": str(myelon_log_path),
                        "summary": {"table": {}},
                    },
                ],
            }

            normalized = report_common.normalize_report(report)
            case_rows = report_common.build_case_rows(normalized)
            side_by_side_rows = report_common.build_side_by_side_rows(normalized)

            self.assertEqual(case_rows[0]["observed_successful_requests_total"], 9)
            self.assertEqual(case_rows[0]["observed_failed_requests_total"], 0)
            self.assertEqual(case_rows[0]["observed_http_422_rejection_count"], 0)
            self.assertFalse(case_rows[0]["observed_request_rejections"])

            self.assertEqual(case_rows[1]["observed_successful_requests_total"], 3)
            self.assertEqual(case_rows[1]["observed_failed_requests_total"], 1)
            self.assertEqual(case_rows[1]["observed_clients_with_failures"], 1)
            self.assertEqual(case_rows[1]["observed_http_422_rejection_count"], 1)
            self.assertTrue(case_rows[1]["observed_request_rejections"])

            metric_map = {row["metric"]: row for row in side_by_side_rows}
            self.assertEqual(
                metric_map["observed_successful_requests_total"]["baseline_value"], 9.0
            )
            self.assertEqual(
                metric_map["observed_successful_requests_total"]["myelon_value"], 3.0
            )
            self.assertEqual(
                metric_map["observed_http_422_rejection_count"]["baseline_value"], 0.0
            )
            self.assertEqual(
                metric_map["observed_http_422_rejection_count"]["myelon_value"], 1.0
            )


if __name__ == "__main__":
    unittest.main()
