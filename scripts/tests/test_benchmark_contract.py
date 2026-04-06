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


class BenchmarkScriptReportTests(unittest.TestCase):
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
            self.assertTrue(summary_md.is_file())
            self.assertTrue(details_csv.is_file())
            self.assertTrue(run_index_md.is_file())
            self.assertTrue(side_by_side_md.is_file())
            self.assertTrue(system_md.is_file())

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
            self.assertEqual(report["cases"][0]["stop_point"], "full_completion")
            self.assertIn("machine_profile", report)
            self.assertIn("model_capability", report)
            self.assertIn("report_bundle", report)
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["details_csv"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["run_index_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["side_by_side_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["system_info"]["md"]).is_file())

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
            self.assertEqual(report["conversation_sampling"], "round_robin")
            self.assertEqual(report["limit_min_tokens"], 8)
            self.assertEqual(report["limit_max_tokens"], 8)
            self.assertTrue(report["workload_file"].endswith("synthetic_server_prefill_stress_round_robin.json"))
            benchmark_command = report["cases"][0]["benchmark_command"]
            self.assertIn("--conversation-sampling", benchmark_command)
            self.assertIn("--limit-min-tokens", benchmark_command)
            self.assertIn("--limit-max-tokens", benchmark_command)
            self.assertNotIn("--warmup-step", benchmark_command)
            run_index_csv = Path(report["report_bundle"]["benchmarks"]["run_index_csv"])
            run_index_text = run_index_csv.read_text(encoding="utf-8")
            self.assertIn("conversation_sampling", run_index_text)
            self.assertIn("round_robin", run_index_text)
            self.assertIn("limit_min_tokens", run_index_text)
            self.assertIn("limit_max_tokens", run_index_text)
            server_command = report["cases"][0]["server_command"]
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
            self.assertTrue(
                report["workload_file"].endswith(
                    "synthetic_server_prefill_shared_prefix_round_robin.json"
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
            self.assertTrue(
                report["workload_file"].endswith(
                    "synthetic_server_prefill_fixed_prompt_burst.json"
                )
            )
            self.assertEqual(report["limit_min_tokens"], 1)
            self.assertEqual(report["limit_max_tokens"], 1)
            self.assertFalse(report["prefix_cache_enabled"])
            server_command = report["cases"][0]["server_command"]
            self.assertIn("--kv-fraction", server_command)
            self.assertNotIn("--max-model-len", server_command)

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
            self.assertEqual(report["cases"][0]["stop_point"], "full_completion")
            self.assertIn("machine_profile", report)
            self.assertIn("model_capability", report)
            self.assertIn("topology_capability", report)
            self.assertIn("report_bundle", report)
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["details_csv"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["run_index_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["side_by_side_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["system_info"]["md"]).is_file())

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
            rollup_run_index_md = Path(outputs["rollup_run_index_md"])
            per_model_side_by_side_md = Path(outputs["per_model_side_by_side_md"])
            all_run_commands_md = Path(outputs["all_run_commands_md"])
            self.assertTrue(current_findings_md.is_file())
            self.assertTrue(rollup_run_index_md.is_file())
            self.assertTrue(per_model_side_by_side_md.is_file())
            self.assertTrue(all_run_commands_md.is_file())

            findings_text = current_findings_md.read_text(encoding="utf-8")
            self.assertIn("Qwen/Qwen3-4B", findings_text)
            self.assertIn("skipped_unsupported_topology", findings_text)

            side_text = per_model_side_by_side_md.read_text(encoding="utf-8")
            self.assertIn("requests_per_sec", side_text)
            self.assertIn("Qwen/Qwen3-4B", side_text)

            commands_text = all_run_commands_md.read_text(encoding="utf-8")
            self.assertIn("All Run Commands", commands_text)


if __name__ == "__main__":
    unittest.main()
