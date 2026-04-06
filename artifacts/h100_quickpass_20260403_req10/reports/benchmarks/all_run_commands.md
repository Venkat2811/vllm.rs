# All Run Commands

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10`

## Qwen/Qwen3.5-27B-FP8 / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen35_27b_fp8/report.json`
- status: `completed`

### runner_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --force-runner --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen35_27b_fp8/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen35_27b_fp8/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step
```

## Qwen/Qwen3-0.6B / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen3_06b/report.json`
- status: `completed`

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
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen3_06b/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen3_06b/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen3_4b/report.json`
- status: `completed`

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
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen3_4b/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_random_qwen3_4b/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-0.6B / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_sharegpt_qwen3_06b/report.json`
- status: `completed`

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
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_sharegpt_qwen3_06b/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_sharegpt_qwen3_06b/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / pd_qos / pd_tp1

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_sharegpt_qwen3_4b/report.json`
- status: `completed`

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
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_sharegpt_qwen3_4b/runner_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon_pd

- pd_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --pd-server --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 0 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- client_server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --pd-client --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --device-ids 1 --myelon-ipc --prefix-cache --pd-url tcp://127.0.0.1:18100
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/pd_tp1_sharegpt_qwen3_4b/myelon_pd/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3.5-27B-FP8 / serving_qos / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen35_27b_fp8/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen35_27b_fp8/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 2e1b21350ce589fcaafbb3c7d7eac526a7aed582
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen35_27b_fp8/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 2e1b21350ce589fcaafbb3c7d7eac526a7aed582
```

## Qwen/Qwen3-0.6B / serving_qos / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen3_06b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen3_06b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen3_06b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / serving_qos / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen3_4b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen3_4b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_random_qwen3_4b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-0.6B / serving_qos / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_sharegpt_qwen3_06b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_sharegpt_qwen3_06b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_sharegpt_qwen3_06b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / serving_qos / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_sharegpt_qwen3_4b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_sharegpt_qwen3_4b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/single_gpu_sharegpt_qwen3_4b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3.5-27B-FP8 / serving_qos / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen35_27b_fp8/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen35_27b_fp8/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 2e1b21350ce589fcaafbb3c7d7eac526a7aed582
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen35_27b_fp8/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-27B-FP8/snapshots/2e1b21350ce589fcaafbb3c7d7eac526a7aed582 --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 2e1b21350ce589fcaafbb3c7d7eac526a7aed582
```

## Qwen/Qwen3-0.6B / serving_qos / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen3_06b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen3_06b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen3_06b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / serving_qos / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen3_4b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen3_4b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 1024 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/synthetic_multi_turn_smoke.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_random_qwen3_4b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-0.6B / serving_qos / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_sharegpt_qwen3_06b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_sharegpt_qwen3_06b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_sharegpt_qwen3_06b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / serving_qos / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_sharegpt_qwen3_4b/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_sharegpt_qwen3_4b/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-model-len 4096 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/b300_benchmarking_2026_04_02/sharegpt_conv_16_mt4_8.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_quickpass_20260403_req10/tp2_sharegpt_qwen3_4b/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 2 --max-turns 2 --max-retries 1 --request-timeout-sec 240 --request-rate 0 --max-num-requests 10 --warmup-step --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

