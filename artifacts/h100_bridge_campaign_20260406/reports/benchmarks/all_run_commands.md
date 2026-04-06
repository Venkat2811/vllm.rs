# All Run Commands

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406`

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt/report.json`
- status: `partial`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-model-len 2560 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_fixed_prompt_burst.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 32 --max-turns 2 --max-retries 1 --request-timeout-sec 300 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 1 --limit-max-tokens 1
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v2/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_fixed_prompt_burst.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v2/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18080 --num-clients 1 --max-active-conversations 32 --max-turns 2 --max-retries 1 --request-timeout-sec 300 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 1 --limit-max-tokens 1 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_fixed_prompt_burst.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v2/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18081 --num-clients 1 --max-active-conversations 32 --max-turns 2 --max-retries 1 --request-timeout-sec 300 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 1 --limit-max-tokens 1 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18080 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18081 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256c/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18080 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256c/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 2560 --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18081 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256c/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v3/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18080 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v3/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 32 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18081 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v3/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 32 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/report.json`
- status: `completed`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18080 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 32 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 2560 --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18081 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v4/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 32 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

