# All Run Commands

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406`

## Qwen/Qwen3-0.6B / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_pd_cold_turn_idle_gap_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `pd_tcp/rpc8192/resp8192/busy_spin/prefix_off`

### runner_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_pd_cold_turn_idle_gap_v1/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 180 --request-rate 1.0 --max-num-requests 32 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_pd_cold_turn_idle_gap_v1/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 180 --request-rate 1.0 --max-num-requests 32 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / serving_qos / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/blocking_wait/prefix_off`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --force-runner --max-model-len 1024
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 180 --request-rate 1.0 --conversation-sampling round_robin --max-num-requests 32 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --max-model-len 1024 --myelon-rpc-depth 8192 --myelon-response-depth 8192
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_single_gpu_cold_turn_idle_gap_v2/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 180 --request-rate 1.0 --conversation-sampling round_robin --max-num-requests 32 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / serving_qos / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_tp2_cold_turn_idle_gap_v2/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 1024 --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_tp2_cold_turn_idle_gap_v2/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 180 --request-rate 1.0 --conversation-sampling round_robin --max-num-requests 32 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 1024 --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_06b_tp2_cold_turn_idle_gap_v2/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 180 --request-rate 1.0 --conversation-sampling round_robin --max-num-requests 32 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_cold_turn_idle_gap_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `pd_tcp/rpc8192/resp8192/busy_spin/prefix_off`

### runner_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_cold_turn_idle_gap_v1/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 300 --request-rate 1.0 --max-num-requests 16 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_cold_turn_idle_gap_v1/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 300 --request-rate 1.0 --max-num-requests 16 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-4B / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `pd_tcp/rpc8192/resp8192/busy_spin/prefix_off`

### runner_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 300 --request-rate 0 --max-num-requests 16 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_idle_gap_campaign_20260406/qwen3_4b_pd_warm_steady_state_v1/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 300 --request-rate 0 --max-num-requests 16 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

