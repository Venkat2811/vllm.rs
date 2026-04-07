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
import myelon_benchmark_common as benchmark_common
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

BENCHMARK_TEXT_WITH_OUTCOME = "\n".join(
    [
        BENCHMARK_TEXT,
        "06-04-2026 12:32:11 [INFO] - Client 0 received a termination signal",
        "06-04-2026 12:32:11 [INFO] - Client 0 is done (num_successes=2, num_failures=1)",
        "06-04-2026 12:32:11 [INFO] - Client 1 has no more work",
        "06-04-2026 12:32:11 [INFO] - Client 1 is done (num_successes=3, num_failures=0)",
        "06-04-2026 12:32:11 [WARN] - Received HTTP status 422 for request 7",
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

SERVER_ATTRIBUTION_LOG_TEXT = "\n".join(
    [
        "2026-04-06T12:25:57.365547Z  INFO vllm_rs::core::engine: Prefilling [seq_id 0]: 100 tokens in 1.00s (100.00 tokens/s)",
        "2026-04-06T12:25:58.365547Z  INFO vllm_rs::core::engine: Prefilling [seq_id 1]: 200 tokens in 2.00s (100.00 tokens/s, cache included)",
        "2026-04-06T12:25:58.965547Z  INFO vllm_rs::core::engine: [Seq 0] ⏱️ FirstTokenPath: scheduler_wait_ms=150 prefill_roundtrip_ms=1200 response_to_emit_ms=25 ingress_to_emit_ms=1375",
        "2026-04-06T12:25:59.965547Z  INFO vllm_rs::core::engine: [Seq 1] ⏱️ FirstTokenPath: scheduler_wait_ms=250 prefill_roundtrip_ms=1700 response_to_emit_ms=50 ingress_to_emit_ms=2000",
        "2026-04-06T12:25:59.365547Z  INFO vllm_rs::server::server: [Seq 0] ⏱️ Prompt: 90 tokens in 0.90s (100.00 t/s)",
        "2026-04-06T12:26:00.365547Z  INFO vllm_rs::server::server: [Seq 1] ⏱️ Prompt: 180 tokens in 1.80s (100.00 t/s)",
        "2026-04-06T12:26:01.365547Z  INFO vllm_rs::server::server: [Seq 0] ⏱️ Decoded: 8 tokens in 4.00s (2.00 t/s)",
        "2026-04-06T12:26:01.465547Z  INFO vllm_rs::server::server: [Seq 0] ⏱️ FirstTokenFlush: emit_to_flush_ms=7 kind=content",
        "2026-04-06T12:26:02.465547Z  INFO vllm_rs::server::server: [Seq 1] ⏱️ FirstTokenFlush: emit_to_flush_ms=11 kind=tool_chunk",
        "2026-04-06T12:26:02.365547Z  INFO vllm_rs::core::block_manager: Prefix cache hit seq 2 (1024 cached tokens, 16 blocks)",
        "2026-04-06T12:26:03.365547Z  INFO vllm_rs::core::block_manager: Prefix cache hit seq 3 (512 cached tokens, 8 blocks)",
        "2026-04-06T12:26:04.365547Z  WARN vllm_rs::core::scheduler: Trying to swap out preempt Seq 5",
        "2026-04-06T12:26:05.365547Z ERROR vllm_rs::core::engine: Unable to schedule task(s), drop the oldest active request (seq_id: 5)",
        "2026-04-06T12:26:06.365547Z ERROR vllm_rs::server::server: Stream generation failed: insufficient remaining kvcache",
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


class ExitedFakeProcess(FakeProcess):
    def __init__(self, returncode: int) -> None:
        super().__init__()
        self.returncode = returncode

    def poll(self) -> int:
        return self.returncode


class FakeStream:
    def __init__(self, text: str) -> None:
        self._lines = text.splitlines(keepends=True)

    def has_pending_data(self) -> bool:
        return bool(self._lines)

    def readline(self) -> str:
        if self._lines:
            return self._lines.pop(0)
        return ""

    def read(self) -> str:
        if not self._lines:
            return ""
        remainder = "".join(self._lines)
        self._lines = []
        return remainder


class FakePrefillProbeProcess:
    def __init__(self, text: str) -> None:
        self.stdout = FakeStream(text)
        self.returncode = None

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: int | None = None) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


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


def complete_first_prefill_run(label: str) -> dict:
    return {
        "label": label,
        "command": ["fake"],
        "exit_code": 0,
        "process_exit_code": -15,
        "stop_point_reached": True,
        "elapsed_seconds": 0.5,
        "metrics": {
            "response": None,
            "first_prefill_tokens": 256,
            "first_prefill_seconds": 2.5,
            "first_prefill_tokens_per_second": 102.4,
            "prompt_tokens": 256,
            "prompt_seconds": 2.5,
            "prompt_tokens_per_second": 102.4,
            "decoded_tokens": None,
            "decode_seconds": None,
            "decode_tokens_per_second": None,
            "myelon_enabled": label.startswith("myelon"),
            "myelon_first_request_logged": label.startswith("myelon"),
            "myelon_first_response_logged": False,
            "socket_shutdown_logged": False,
            "myelon_shutdown_logged": False,
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


def complete_batch_completion_run(label: str) -> dict:
    return {
        "label": label,
        "command": ["fake"],
        "exit_code": 0,
        "elapsed_seconds": 1.5,
        "metrics": {
            "response": None,
            "first_prefill_tokens": 17,
            "first_prefill_seconds": 1.35,
            "first_prefill_tokens_per_second": 12.64,
            "prompt_tokens": 2048,
            "prompt_seconds": 1.35,
            "prompt_tokens_per_second": 1522.68,
            "decoded_tokens": 128,
            "decode_seconds": 0.06,
            "decode_tokens_per_second": 1976.6,
            "myelon_enabled": label.startswith("myelon"),
            "myelon_first_request_logged": label.startswith("myelon"),
            "myelon_first_response_logged": False,
            "socket_shutdown_logged": True,
            "myelon_shutdown_logged": False,
            "runner_prefill_error_logged": False,
            "engine_loop_error_logged": False,
            "error_logged": False,
            "runner_mode": "process",
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
    def test_wait_for_server_ready_fails_fast_when_server_exits(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "server exited before readiness with code 9",
        ):
            server_matrix.wait_for_server_ready(
                "http://127.0.0.1:18080",
                timeout_seconds=10,
                server_process=ExitedFakeProcess(9),
            )

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
            tp_scale_overlay="tp2",
            prefill_tp_size=2,
            decode_tp_size=2,
            pd_enabled=False,
            pd_role_layout=None,
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
        self.assertEqual(contract["tp_scale_overlay"], "tp2")
        self.assertEqual(contract["prefill_tp_size"], 2)
        self.assertEqual(contract["decode_tp_size"], 2)
        self.assertFalse(contract["pd_enabled"])
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

    def test_run_case_until_first_prefill_captures_prefill_metrics(self) -> None:
        output = "\n".join(
            [
                "2026-04-06T12:25:52.000000Z  WARN vllm_rs::utils: Runner topology mode=process reason=forced_runner num_shards=2 device_ids=[0, 1]",
                "2026-04-06T12:25:57.365547Z  INFO vllm_rs::core::engine: Prefilling [seq_id 0]: 100 tokens in 1.00s (100.00 tokens/s)",
            ]
        )

        def fake_select(readers, _writers, _errors, _timeout):
            stream = readers[0]
            return ([stream], [], []) if stream.has_pending_data() else ([], [], [])

        with mock.patch.object(
            benchmark_common.subprocess,
            "Popen",
            return_value=FakePrefillProbeProcess(output),
        ), mock.patch.object(
            benchmark_common.select,
            "select",
            side_effect=fake_select,
        ):
            run = benchmark_common.run_case_until_first_prefill(
                repo_root=Path("."),
                label="runner-probe",
                command=["fake"],
                timeout_seconds=5,
            )

        self.assertEqual(run["exit_code"], 0)
        self.assertTrue(run["stop_point_reached"])
        self.assertEqual(run["metrics"]["first_prefill_tokens"], 100)
        self.assertEqual(run["metrics"]["first_prefill_seconds"], 1.0)
        self.assertEqual(run["metrics"]["prompt_tokens"], 100)
        self.assertEqual(run["metrics"]["prompt_tokens_per_second"], 100.0)

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

    def test_pd_topology_capability_supports_disjoint_multidevice_roles(self) -> None:
        capability = validation_common.classify_pd_topology_capability(
            server_device_ids=[0, 1],
            client_device_ids=[2, 3],
            detected_cuda_device_count=4,
        )
        self.assertTrue(capability["pd_supported"])
        self.assertIsNone(capability["pd_skip_reason"])

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

    def test_pd_transport_capability_rejects_localipc_multidevice_roles(self) -> None:
        capability = validation_common.classify_pd_transport_capability(
            "pd_localipc_default",
            server_device_ids=[0, 1],
            client_device_ids=[2, 3],
        )
        self.assertFalse(capability["pd_supported"])
        self.assertEqual(
            capability["pd_skip_reason"],
            "unsupported_transport_localipc_multidevice_roles_unqualified",
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

    def test_infer_report_status_treats_planned_stop_point_probe_as_completed(self) -> None:
        status = report_common.infer_report_status(
            {
                "status": "partial",
                "benchmark_contract": {
                    "stop_point": "minimal_decode_completion",
                },
                "cases": [
                    {
                        "label": "runner",
                        "stop_point": "minimal_decode_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                    },
                    {
                        "label": "myelon",
                        "stop_point": "minimal_decode_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                    },
                ],
            }
        )
        self.assertEqual(status, "completed")

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

    def test_normalize_report_marks_stop_point_probe_completed(self) -> None:
        normalized = report_common.normalize_report(
            {
                "status": "partial",
                "benchmark_contract": {
                    "benchmark_family": "prefill_stress",
                    "benchmark_submode": "fixed_prompt_burst",
                    "question_answered": "prefill",
                    "workload_class": "synthetic_prompt_short_burst",
                    "warmup_policy": "cli_warmup_runs:1",
                    "first_turn_measured": True,
                    "arrival_pattern": "prompt_burst_serial_runs",
                    "concurrency_policy": {"driver": "cli_batch_burst_repeated_invocation"},
                    "cache_pressure_profile": "unspecified",
                    "equivalence_group": None,
                    "topology_overlay": "tp2",
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "fullpass",
                    "stop_point": "first_prefill_completion",
                    "skip_reason": None,
                },
                "cases": [
                    {
                        "label": "runner",
                        "stop_point": "first_prefill_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                    },
                    {
                        "label": "myelon",
                        "stop_point": "first_prefill_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                    },
                ],
            }
        )
        self.assertEqual(normalized["status"], "completed")
        self.assertEqual(normalized["result_boundary"], "stop_point_limited")

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
        self.assertEqual(rows[0]["tp_scale_overlay"], "tp2")
        self.assertEqual(rows[0]["prefill_tp_size"], 2)
        self.assertEqual(rows[0]["decode_tp_size"], 2)

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

    def test_normalize_report_backfills_server_path_attribution_from_server_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            benchmark_log = tmp_path / "benchmark.log"
            server_log = tmp_path / "server.log"
            benchmark_log.write_text(BENCHMARK_TEXT, encoding="utf-8")
            server_log.write_text(SERVER_ATTRIBUTION_LOG_TEXT, encoding="utf-8")

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

            attribution = normalized["cases"][0]["observed_server_path_attribution"]
            self.assertEqual(attribution["observed_prefill_event_count"], 2)
            self.assertEqual(attribution["observed_prefill_tokens_total"], 300)
            self.assertEqual(attribution["observed_prefill_seconds_total"], 3.0)
            self.assertEqual(attribution["observed_prefill_tps_mean"], 100.0)
            self.assertEqual(attribution["observed_prompt_metric_event_count"], 2)
            self.assertEqual(attribution["observed_prompt_tokens_total"], 270)
            self.assertEqual(attribution["observed_prompt_seconds_total"], 2.7)
            self.assertEqual(attribution["observed_decode_metric_event_count"], 1)
            self.assertEqual(attribution["observed_decode_tokens_total"], 8)
            self.assertEqual(attribution["observed_decode_seconds_total"], 4.0)
            self.assertEqual(attribution["observed_decode_tps_mean"], 2.0)
            self.assertEqual(attribution["observed_prefix_cache_hit_count"], 2)
            self.assertEqual(attribution["observed_prefix_cache_hit_tokens_total"], 1536)
            self.assertEqual(attribution["observed_first_token_path_event_count"], 2)
            self.assertEqual(attribution["observed_scheduler_wait_ms_total"], 400)
            self.assertEqual(attribution["observed_scheduler_wait_ms_mean"], 200.0)
            self.assertEqual(attribution["observed_prefill_roundtrip_ms_total"], 2900)
            self.assertEqual(attribution["observed_prefill_roundtrip_ms_mean"], 1450.0)
            self.assertEqual(attribution["observed_response_to_emit_ms_total"], 75)
            self.assertEqual(attribution["observed_response_to_emit_ms_mean"], 37.5)
            self.assertEqual(attribution["observed_ingress_to_emit_ms_total"], 3375)
            self.assertEqual(attribution["observed_ingress_to_emit_ms_mean"], 1687.5)
            self.assertEqual(attribution["observed_first_token_flush_count"], 2)
            self.assertEqual(attribution["observed_emit_to_flush_ms_total"], 18)
            self.assertEqual(attribution["observed_emit_to_flush_ms_mean"], 9.0)
            self.assertEqual(attribution["observed_swap_out_attempt_count"], 1)
            self.assertEqual(attribution["observed_dropped_request_count"], 1)
            self.assertEqual(attribution["observed_stream_generation_failed_count"], 1)

            summary_attribution = normalized["cases"][0]["summary"][
                "observed_server_path_attribution"
            ]
            self.assertEqual(summary_attribution["observed_prefill_event_count"], 2)

            case_rows = report_common.build_case_rows(normalized)
            self.assertEqual(case_rows[0]["observed_prefill_event_count"], 2)
            self.assertEqual(case_rows[0]["observed_prompt_seconds_total"], 2.7)
            self.assertEqual(case_rows[0]["observed_scheduler_wait_ms_total"], 400)
            self.assertEqual(case_rows[0]["observed_emit_to_flush_ms_mean"], 9.0)
            self.assertEqual(case_rows[0]["observed_swap_out_attempt_count"], 1)


class BenchmarkScriptReportTests(unittest.TestCase):
    def test_cli_prepare_cases_supports_tp8_mode(self) -> None:
        self.assertEqual(
            benchmark_matrix.prepare_cases("tp8", None),
            [
                ("runner", ["--num-shards", "8", "--force-runner"]),
                ("myelon", ["--num-shards", "8", "--myelon-ipc"]),
            ],
        )

    def test_server_prepare_cases_supports_tp8_mode(self) -> None:
        self.assertEqual(
            server_matrix.prepare_cases("tp8"),
            [
                ("runner", ["--num-shards", "8", "--force-runner"]),
                ("myelon", ["--num-shards", "8", "--myelon-ipc"]),
            ],
        )

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
                    "run_case_for_stop_point_with_retries",
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
            self.assertEqual(report["benchmark_contract"]["tp_scale_overlay"], "tp2")
            self.assertEqual(report["benchmark_contract"]["prefill_tp_size"], 2)
            self.assertEqual(report["benchmark_contract"]["decode_tp_size"], 2)
            self.assertFalse(report["benchmark_contract"]["pd_enabled"])
            self.assertEqual(report["benchmark_contract"]["run_class"], "quickpass")
            self.assertEqual(report["benchmark_contract"]["stop_point"], "full_completion")
            self.assertEqual(
                report["benchmark_contract"]["workload_class"],
                "synthetic_prompt_short_burst",
            )
            self.assertEqual(
                report["benchmark_contract"]["concurrency_policy"]["batch_size"],
                256,
            )
            self.assertEqual(report["status"], "completed")
            self.assertIn("--batch", report["cases"][0]["command"])
            self.assertIn("256", report["cases"][0]["command"])
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

    def test_cli_benchmark_report_supports_tp8_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_path = tmp_path / "cli_tp8_report.json"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_OUT": str(output_path),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_BENCHMARK_MODE": "tp8",
                "VLLM_BENCHMARK_WARMUP_RUNS": "0",
                "VLLM_BENCHMARK_MEASURED_RUNS": "1",
                "VLLM_CAPTURE_RAW_SYSTEM_INFO": "0",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    benchmark_matrix,
                    "validate_requested_topology",
                    return_value=8,
                ), mock.patch.object(
                    benchmark_matrix.subprocess,
                    "run",
                    return_value=CompletedProcess(["cargo"], 0, "", ""),
                ), mock.patch.object(
                    benchmark_matrix,
                    "run_case_for_stop_point_with_retries",
                    side_effect=[
                        complete_batch_completion_run("runner-measured-1"),
                        complete_batch_completion_run("myelon-measured-1"),
                    ],
                ):
                    rc = benchmark_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["topology_overlay"], "tp8")
            self.assertEqual(report["benchmark_contract"]["tp_scale_overlay"], "tp8")
            self.assertEqual(report["benchmark_contract"]["prefill_tp_size"], 8)
            self.assertEqual(report["benchmark_contract"]["decode_tp_size"], 8)
            self.assertEqual(
                report["benchmark_contract"]["concurrency_policy"]["expected_num_shards"],
                8,
            )
            self.assertEqual(report["cases"][0]["command"].count("--num-shards"), 1)
            self.assertIn("8", report["cases"][0]["command"])
            self.assertIn("--force-runner", report["cases"][0]["command"])
            self.assertIn("--myelon-ipc", report["cases"][1]["command"])

    def test_cli_benchmark_minimal_decode_defaults_stop_point_from_max_tokens_one(self) -> None:
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
                "VLLM_BENCHMARK_WARMUP_RUNS": "0",
                "VLLM_BENCHMARK_MEASURED_RUNS": "1",
                "VLLM_MAX_TOKENS": "1",
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
                    "run_case_for_stop_point_with_retries",
                    side_effect=[
                        complete_batch_completion_run("runner-measured-1"),
                        complete_batch_completion_run("myelon-measured-1"),
                    ],
                ):
                    rc = benchmark_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                report["benchmark_contract"]["stop_point"],
                "minimal_decode_completion",
            )
            self.assertEqual(report["cases"][0]["stop_point"], "minimal_decode_completion")

    def test_cli_benchmark_honors_explicit_batch_size_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_path = tmp_path / "cli_batch_report.json"
            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_OUT": str(output_path),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_BENCHMARK_MODE": "tp2",
                "VLLM_BENCHMARK_WARMUP_RUNS": "0",
                "VLLM_BENCHMARK_MEASURED_RUNS": "1",
                "VLLM_BENCHMARK_BATCH_SIZE": "64",
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
                    "run_case_for_stop_point_with_retries",
                    side_effect=[
                        complete_batch_completion_run("runner-measured-1"),
                        complete_batch_completion_run("myelon-measured-1"),
                    ],
                ):
                    rc = benchmark_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["batch_size"], 64)
            self.assertEqual(
                report["benchmark_contract"]["concurrency_policy"]["batch_size"],
                64,
            )
            self.assertIn("--batch", report["cases"][0]["command"])
            self.assertIn("64", report["cases"][0]["command"])

    def test_cli_benchmark_first_prefill_probe_records_prefill_stop_point(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_path = tmp_path / "cli_probe_report.json"
            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_OUT": str(output_path),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_BENCHMARK_MODE": "tp2",
                "VLLM_BENCHMARK_WARMUP_RUNS": "0",
                "VLLM_BENCHMARK_MEASURED_RUNS": "1",
                "VLLM_PREFILL_STRESS_STOP_POINT": "first_prefill_completion",
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
                    "run_case_for_stop_point_with_retries",
                    side_effect=[
                        complete_first_prefill_run("runner-measured-1"),
                        complete_first_prefill_run("myelon-measured-1"),
                    ],
                ):
                    rc = benchmark_matrix.main()

            self.assertEqual(rc, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                report["benchmark_contract"]["stop_point"],
                "first_prefill_completion",
            )
            self.assertEqual(report["cases"][0]["stop_point"], "first_prefill_completion")
            self.assertEqual(report["cases"][0]["sample_response"], None)
            self.assertEqual(
                report["comparisons"]["myelon_first_prefill_tps_ratio_vs_runner"],
                1.0,
            )

    def test_cli_benchmark_rejects_invalid_stop_point(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            output_path = tmp_path / "cli_invalid_report.json"
            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_OUT": str(output_path),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PREFILL_STRESS_STOP_POINT": "bad_mode",
            }

            with mock.patch.dict(os.environ, env, clear=False):
                rc = benchmark_matrix.main()

            self.assertEqual(rc, 1)
            self.assertFalse(output_path.exists())

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
                return CompletedProcess(command, 0, BENCHMARK_TEXT_WITH_OUTCOME, "")

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
            self.assertEqual(report["benchmark_contract"]["tp_scale_overlay"], "tp1")
            self.assertEqual(report["benchmark_contract"]["prefill_tp_size"], 1)
            self.assertEqual(report["benchmark_contract"]["decode_tp_size"], 1)
            self.assertFalse(report["benchmark_contract"]["pd_enabled"])
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
            observed_outcome = report["cases"][0]["summary"]["observed_benchmark_outcome"]
            self.assertEqual(observed_outcome["observed_successful_requests_total"], 5)
            self.assertEqual(observed_outcome["observed_failed_requests_total"], 1)
            self.assertEqual(observed_outcome["observed_clients_with_failures"], 1)
            self.assertEqual(observed_outcome["observed_client_no_more_work_count"], 1)
            self.assertEqual(observed_outcome["observed_client_termination_signal_count"], 1)
            self.assertEqual(observed_outcome["observed_http_422_rejection_count"], 1)
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

    def test_server_benchmark_report_supports_tp8_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "synthetic_multi_turn_smoke.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "server_tp8_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_SERVER_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_SERVER_BENCHMARK_MODE": "tp8",
                "VLLM_SERVER_BENCH_MAX_NUM_REQUESTS": "10",
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
                    return_value=8,
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
            self.assertEqual(report["benchmark_contract"]["topology_overlay"], "tp8")
            self.assertEqual(report["benchmark_contract"]["tp_scale_overlay"], "tp8")
            self.assertEqual(report["benchmark_contract"]["prefill_tp_size"], 8)
            self.assertEqual(report["benchmark_contract"]["decode_tp_size"], 8)
            self.assertEqual(report["effective_device_ids"], list(range(8)))
            runner_command = report["cases"][0]["server_command"]
            self.assertIn("--num-shards", runner_command)
            self.assertIn("8", runner_command)
            self.assertIn("--force-runner", runner_command)
            self.assertIn("--device-ids", runner_command)
            self.assertIn("0,1,2,3,4,5,6,7", runner_command)

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
            self.assertEqual(report["max_model_len"], 2560)
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
            self.assertIn("--max-model-len", server_command)
            self.assertIn("2560", server_command)
            self.assertNotIn("--kv-fraction", server_command)
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
            self.assertEqual(report["max_model_len"], 2560)
            server_command = report["cases"][0]["server_command"]
            self.assertIn("--max-num-seqs", server_command)
            self.assertIn("256", server_command)
            self.assertIn("--max-model-len", server_command)
            self.assertIn("2560", server_command)
            self.assertNotIn("--kv-fraction", server_command)

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
            self.assertEqual(report["benchmark_contract"]["tp_scale_overlay"], "pd(tp1/tp1)")
            self.assertEqual(report["benchmark_contract"]["prefill_tp_size"], 1)
            self.assertEqual(report["benchmark_contract"]["decode_tp_size"], 1)
            self.assertTrue(report["benchmark_contract"]["pd_enabled"])
            self.assertEqual(report["benchmark_contract"]["pd_role_layout"], "same_host_split_roles")
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

    def test_pd_benchmark_report_supports_tp2_per_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_dir = tmp_path / "model"
            model_dir.mkdir()
            workload_file = tmp_path / "pd_transfer_first_request.json"
            workload_file.write_text("{}\n", encoding="utf-8")
            output_dir = tmp_path / "pd_tp2_out"

            env = {
                "VLLM_MODEL_PATH": str(model_dir),
                "VLLM_BENCHMARK_INPUT_FILE": str(workload_file),
                "VLLM_PD_BENCHMARK_OUT_DIR": str(output_dir),
                "VLLM_BUILD_FEATURES": "cuda,myelon,nccl",
                "VLLM_PD_SERVER_DEVICE_IDS": "0,1",
                "VLLM_PD_CLIENT_DEVICE_IDS": "2,3",
                "VLLM_PD_URL": "tcp://127.0.0.1:18081",
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
                    "terminate_process",
                    return_value=0,
                ), mock.patch.object(
                    pd_matrix,
                    "detect_cuda_device_count",
                    return_value=4,
                ):
                    rc = pd_matrix.main()

            self.assertEqual(rc, 0)
            report_path = output_dir / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["benchmark_contract"]["topology_overlay"], "pd_tp2")
            self.assertEqual(report["benchmark_contract"]["tp_scale_overlay"], "pd(tp2/tp2)")
            self.assertEqual(report["benchmark_contract"]["prefill_tp_size"], 2)
            self.assertEqual(report["benchmark_contract"]["decode_tp_size"], 2)
            self.assertEqual(report["benchmark_contract"]["transport_mode"], "pd_tcp")
            for case in report["cases"]:
                self.assertEqual(
                    case["pd_server_command"][case["pd_server_command"].index("--num-shards") + 1],
                    "2",
                )
                self.assertEqual(
                    case["client_server_command"][case["client_server_command"].index("--num-shards") + 1],
                    "2",
                )

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
            campaign_c = tmp_path / "tp2_prefill_qwen30ba3b"
            campaign_d = tmp_path / "tp2_server_fixed_prompt_qwen30ba3b"
            campaign_a.mkdir()
            campaign_b.mkdir()
            campaign_c.mkdir()
            campaign_d.mkdir()

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
            report_c = {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "prefill_stress",
                    "benchmark_submode": "fixed_prompt_burst",
                    "workload_class": "custom_prompt_env_burst",
                    "topology_overlay": "tp2",
                    "tp_scale_overlay": "tp2",
                    "prefill_tp_size": 2,
                    "decode_tp_size": 2,
                    "pd_enabled": False,
                    "pd_role_layout": None,
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "fullpass",
                    "equivalence_group": "fixed_prompt_burst_bridge",
                    "stop_point": "minimal_decode_completion",
                    "skip_reason": None,
                },
                "machine_profile": {
                    "hostname": "hazy-instance-completes-fin-02",
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
                        "stop_point": "minimal_decode_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "summary": {},
                        "measured_summary": {
                            "first_prefill_seconds": {"mean": 1.48},
                            "first_prefill_tokens_per_second": {"mean": 11.63},
                            "prompt_seconds": {"mean": 1.48},
                            "prompt_tokens_per_second": {"mean": 1401.14},
                            "decode_seconds": {"mean": 0.063333},
                            "decode_tokens_per_second": {"mean": 1939.38},
                        },
                    },
                    {
                        "label": "myelon",
                        "execution_variant": "myelon",
                        "stop_point": "minimal_decode_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "summary": {},
                        "measured_summary": {
                            "first_prefill_seconds": {"mean": 1.36},
                            "first_prefill_tokens_per_second": {"mean": 12.49},
                            "prompt_seconds": {"mean": 1.36},
                            "prompt_tokens_per_second": {"mean": 1504.67},
                            "decode_seconds": {"mean": 0.06},
                            "decode_tokens_per_second": {"mean": 2024.07},
                        },
                    },
                ],
            }
            report_d = {
                "status": "completed",
                "benchmark_contract": {
                    "benchmark_family": "server_prefill_stress",
                    "benchmark_submode": "fixed_prompt_burst",
                    "workload_class": "synthetic_server_prefill_fixed_prompt_burst",
                    "topology_overlay": "tp2",
                    "tp_scale_overlay": "tp2",
                    "prefill_tp_size": 2,
                    "decode_tp_size": 2,
                    "pd_enabled": False,
                    "pd_role_layout": None,
                    "transport_mode": "socket_vs_myelon_process_runner",
                    "run_class": "quickpass",
                    "equivalence_group": "fixed_prompt_burst_bridge",
                    "stop_point": "full_completion",
                    "skip_reason": None,
                },
                "machine_profile": {
                    "hostname": "hazy-instance-completes-fin-02",
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
                        "summary": {
                            "requests_per_sec": 10.0,
                            "runtime_sec": 3.0,
                            "table": {
                                "ttft_ms": {"mean": 500.0},
                                "tpot_ms": {"mean": 10.0},
                                "latency_ms": {"mean": 1500.0},
                            },
                        },
                        "observed_cache_pressure": {
                            "requested_cache_pressure_profile": "relaxed",
                            "pressure_profile_outcome": "requested_relaxed_observed",
                            "observed_cache_pressure_level": "minimal_pressure",
                        },
                        "observed_server_path_attribution": {
                            "observed_prefill_tps_mean": 520.0,
                            "observed_prompt_tps_mean": 510.0,
                            "observed_prefill_roundtrip_ms_mean": 480.0,
                            "observed_ingress_to_emit_ms_mean": 620.0,
                        },
                    },
                    {
                        "label": "myelon",
                        "execution_variant": "myelon",
                        "stop_point": "full_completion",
                        "skip_reason": None,
                        "benchmark_exit_code": 0,
                        "summary": {
                            "requests_per_sec": 10.5,
                            "runtime_sec": 2.9,
                            "table": {
                                "ttft_ms": {"mean": 450.0},
                                "tpot_ms": {"mean": 9.5},
                                "latency_ms": {"mean": 1400.0},
                            },
                        },
                        "observed_cache_pressure": {
                            "requested_cache_pressure_profile": "relaxed",
                            "pressure_profile_outcome": "requested_relaxed_observed",
                            "observed_cache_pressure_level": "minimal_pressure",
                        },
                        "observed_server_path_attribution": {
                            "observed_prefill_tps_mean": 690.0,
                            "observed_prompt_tps_mean": 680.0,
                            "observed_prefill_roundtrip_ms_mean": 310.0,
                            "observed_ingress_to_emit_ms_mean": 470.0,
                        },
                    },
                ],
            }
            (campaign_a / "report.json").write_text(json.dumps(report_a), encoding="utf-8")
            (campaign_b / "report.json").write_text(json.dumps(report_b), encoding="utf-8")
            (campaign_c / "report.json").write_text(json.dumps(report_c), encoding="utf-8")
            (campaign_d / "report.json").write_text(json.dumps(report_d), encoding="utf-8")

            outputs = report_common.write_rollup_reports(tmp_path)

            current_findings_md = Path(outputs["current_findings_md"])
            high_level_summary_md = Path(outputs["high_level_summary_md"])
            bridge_attribution_md = Path(outputs["bridge_attribution_md"])
            rollup_run_index_md = Path(outputs["rollup_run_index_md"])
            per_model_side_by_side_md = Path(outputs["per_model_side_by_side_md"])
            all_run_commands_md = Path(outputs["all_run_commands_md"])
            family_root = tmp_path / "reports" / "benchmarks" / "by_family"
            equivalence_root = tmp_path / "reports" / "benchmarks" / "by_equivalence"
            workload_root = tmp_path / "reports" / "benchmarks" / "by_workload"
            topology_root = tmp_path / "reports" / "benchmarks" / "by_topology"
            model_root = tmp_path / "reports" / "benchmarks" / "by_model"
            run_class_root = tmp_path / "reports" / "benchmarks" / "by_run_class"
            result_boundary_root = (
                tmp_path / "reports" / "benchmarks" / "by_result_boundary"
            )
            artifact_class_root = (
                tmp_path / "reports" / "benchmarks" / "by_artifact_class"
            )
            pressure_outcome_root = (
                tmp_path / "reports" / "benchmarks" / "by_pressure_outcome_pair"
            )
            self.assertTrue(current_findings_md.is_file())
            self.assertTrue(high_level_summary_md.is_file())
            self.assertTrue(bridge_attribution_md.is_file())
            self.assertTrue(rollup_run_index_md.is_file())
            self.assertTrue(per_model_side_by_side_md.is_file())
            self.assertTrue(all_run_commands_md.is_file())
            self.assertTrue((family_root / "prefill_stress" / "findings.md").is_file())
            self.assertTrue(
                (family_root / "server_prefill_stress" / "findings.md").is_file()
            )
            self.assertTrue(
                (
                    equivalence_root
                    / "fixed_prompt_burst_bridge"
                    / "matched_runs.md"
                ).is_file()
            )
            self.assertTrue(
                (
                    workload_root
                    / "synthetic_server_prefill_fixed_prompt_burst"
                    / "findings.md"
                ).is_file()
            )
            self.assertTrue((topology_root / "tp2" / "findings.md").is_file())
            self.assertTrue(
                (model_root / "qwen_qwen3_30b_a3b" / "findings.md").is_file()
            )
            self.assertTrue((run_class_root / "fullpass" / "findings.md").is_file())
            self.assertTrue(
                (result_boundary_root / "benchmark_complete" / "findings.md").is_file()
            )
            self.assertTrue(
                any(
                    path.is_file()
                    for path in artifact_class_root.glob(
                        "quickpass_benchmark_complete_full_completion/findings.md"
                    )
                )
            )
            self.assertTrue(
                any(
                    path.is_file()
                    for path in pressure_outcome_root.glob(
                        "requested_relaxed_observed_requested_relaxed_observed/findings.md"
                    )
                )
            )

            findings_text = current_findings_md.read_text(encoding="utf-8")
            self.assertIn("Qwen/Qwen3-4B", findings_text)
            self.assertIn("skipped_unsupported_topology", findings_text)
            self.assertIn("Pressure Outcome Pair Counts", findings_text)

            high_level_text = high_level_summary_md.read_text(encoding="utf-8")
            self.assertIn("Pressure Outcome Pair Counts", high_level_text)
            self.assertIn("Strongest Requests/sec Gains", high_level_text)
            self.assertIn("Strongest Prompt Throughput Gains", high_level_text)
            self.assertIn("Strongest First-Prefill Wins", high_level_text)
            self.assertIn("Strongest Prefill-Roundtrip Wins", high_level_text)
            self.assertIn("Qwen/Qwen3-30B-A3B", high_level_text)
            self.assertIn("Incomplete / Unsupported", high_level_text)
            self.assertNotIn("No prompt-throughput deltas were available.", high_level_text)
            self.assertIn("680", high_level_text)
            self.assertIn("310", high_level_text)

            bridge_text = bridge_attribution_md.read_text(encoding="utf-8")
            self.assertIn("Bridge Attribution Summary", bridge_text)
            self.assertIn("Strongest Prompt Gains That Compressed End To End", bridge_text)
            self.assertIn("prompt_gain_compressed", bridge_text)
            self.assertIn("requested_relaxed_observed", bridge_text)
            self.assertIn("Qwen/Qwen3-30B-A3B", bridge_text)
            self.assertIn("No rejection-limited bridge runs were available.", bridge_text)

            side_text = per_model_side_by_side_md.read_text(encoding="utf-8")
            self.assertIn("requests_per_sec", side_text)
            self.assertIn("Qwen/Qwen3-4B", side_text)

            commands_text = all_run_commands_md.read_text(encoding="utf-8")
            self.assertIn("All Run Commands", commands_text)

            family_text = (
                family_root / "server_prefill_stress" / "findings.md"
            ).read_text(encoding="utf-8")
            self.assertIn("server_prefill_stress", family_text)
            self.assertIn("Qwen/Qwen3-30B-A3B", family_text)

            equivalence_text = (
                equivalence_root / "fixed_prompt_burst_bridge" / "matched_runs.md"
            ).read_text(encoding="utf-8")
            self.assertIn("fixed_prompt_burst_bridge", equivalence_text)
            self.assertIn("prefill_stress", equivalence_text)
            self.assertIn("server_prefill_stress", equivalence_text)

            workload_text = (
                workload_root
                / "synthetic_server_prefill_fixed_prompt_burst"
                / "findings.md"
            ).read_text(encoding="utf-8")
            self.assertIn("synthetic_server_prefill_fixed_prompt_burst", workload_text)
            self.assertIn("Qwen/Qwen3-30B-A3B", workload_text)

            topology_text = (
                topology_root / "tp2" / "findings.md"
            ).read_text(encoding="utf-8")
            self.assertIn("tp2", topology_text)
            self.assertIn("Qwen/Qwen3-30B-A3B", topology_text)

            model_text = (
                model_root / "qwen_qwen3_30b_a3b" / "findings.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Qwen/Qwen3-30B-A3B", model_text)
            self.assertIn("server_prefill_stress", model_text)

            run_class_text = (
                run_class_root / "fullpass" / "findings.md"
            ).read_text(encoding="utf-8")
            self.assertIn("fullpass", run_class_text)
            self.assertIn("Qwen/Qwen3-30B-A3B", run_class_text)

            result_boundary_text = (
                result_boundary_root / "benchmark_complete" / "findings.md"
            ).read_text(encoding="utf-8")
            self.assertIn("benchmark_complete", result_boundary_text)

            artifact_class_path = next(
                artifact_class_root.glob(
                    "quickpass_benchmark_complete_full_completion/findings.md"
                )
            )
            artifact_class_text = artifact_class_path.read_text(encoding="utf-8")
            self.assertIn("quickpass/benchmark_complete/full_completion", artifact_class_text)

            pressure_outcome_path = next(
                pressure_outcome_root.glob(
                    "requested_relaxed_observed_requested_relaxed_observed/findings.md"
                )
            )
            pressure_outcome_text = pressure_outcome_path.read_text(encoding="utf-8")
            self.assertIn(
                "requested_relaxed_observed -> requested_relaxed_observed",
                pressure_outcome_text,
            )

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
