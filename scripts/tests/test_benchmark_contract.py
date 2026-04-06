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
            topology_overlay="tp2",
            transport_mode="socket_vs_myelon_process_runner",
            run_class="quickpass",
            stop_point="full_completion",
            skip_reason=None,
        )
        self.assertEqual(contract["benchmark_family"], "prefill_stress")
        self.assertEqual(contract["benchmark_submode"], "fixed_prompt_burst")
        self.assertEqual(contract["run_class"], "quickpass")
        self.assertIn("concurrency_policy", contract)

    def test_run_class_helpers(self) -> None:
        self.assertEqual(validation_common.infer_cli_run_class(5), "fullpass")
        self.assertEqual(validation_common.infer_request_run_class(10), "quickpass")
        self.assertEqual(
            validation_common.resolve_run_class("smoke", "fullpass"),
            "smoke",
        )


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
            self.assertIn("machine_profile", report)
            self.assertIn("report_bundle", report)
            summary_md = Path(report["report_bundle"]["benchmarks"]["summary_md"])
            details_csv = Path(report["report_bundle"]["benchmarks"]["details_csv"])
            system_md = Path(report["report_bundle"]["system_info"]["md"])
            self.assertTrue(summary_md.is_file())
            self.assertTrue(details_csv.is_file())
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
            self.assertEqual(
                report["benchmark_contract"]["transport_mode"],
                "socket_vs_myelon_process_runner",
            )
            self.assertEqual(report["benchmark_contract"]["run_class"], "quickpass")
            self.assertEqual(report["cases"][0]["stop_point"], "full_completion")
            self.assertIn("machine_profile", report)
            self.assertIn("report_bundle", report)
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["details_csv"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["system_info"]["md"]).is_file())

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
            self.assertEqual(report["cases"][0]["stop_point"], "full_completion")
            self.assertIn("machine_profile", report)
            self.assertIn("report_bundle", report)
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["summary_md"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["benchmarks"]["details_csv"]).is_file())
            self.assertTrue(Path(report["report_bundle"]["system_info"]["md"]).is_file())


if __name__ == "__main__":
    unittest.main()
