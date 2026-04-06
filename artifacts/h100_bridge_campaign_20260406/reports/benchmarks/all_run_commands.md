# All Run Commands

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406`

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_swap_v10/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix512/cpufold2.0`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19320 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 8192 --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 512 --cpu-mem-fold 2.0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_swap_v10/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:19320 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 1200 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 32 --limit-max-tokens 32 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19321 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 8192 --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 512 --cpu-mem-fold 2.0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_swap_v10/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:19321 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 1200 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 32 --limit-max-tokens 32 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_swap_v9/report.json`
- status: `partial`
- artifact_class: `fullpass/benchmark_failed/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix512/kv0.04/cpufold2.0`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19220 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 512 --kv-fraction 0.04 --cpu-mem-fold 2.0
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_swap_v9/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:19220 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 1200 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 32 --limit-max-tokens 32 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v1/report.json`
- status: `partial`
- artifact_class: `fullpass/benchmark_failed/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix4096/kv0.35/cpufold0.1`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18180 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18180 --num-clients 1 --max-active-conversations 16 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18181 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18181 --num-clients 1 --max-active-conversations 16 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v2/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix4096/kv0.35/cpufold0.1`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18220 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v2/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18220 --num-clients 1 --max-active-conversations 16 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18221 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v2/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18221 --num-clients 1 --max-active-conversations 16 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v3/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix4096/kv0.35/cpufold0.1`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18420 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v3/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18420 --num-clients 1 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18421 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v3/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18421 --num-clients 1 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix4096/kv0.35/cpufold0.1`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18520 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18520 --num-clients 1 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18521 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v4/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18521 --num-clients 1 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v5/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix4096/kv0.35/cpufold0.1`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18620 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v5/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18620 --num-clients 8 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18621 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 4096 --kv-fraction 0.35 --cpu-mem-fold 0.1
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v5/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18621 --num-clients 8 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v6/report.json`
- status: `partial`
- artifact_class: `fullpass/benchmark_failed/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix1024/kv0.08/cpufold0.05`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18820 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v6/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18820 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v8/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix1024/kv0.08/cpufold0.05`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19020 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v8/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:19020 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19021 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_cache_thrash_rr_v8/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:19021 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt/report.json`
- status: `partial`
- artifact_class: `fullpass/runtime_limited/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/prefix_off/kv0.55/cpufold0.5`

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

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18080 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v1/runner/conversations.json --prompt-text Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 1200 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18081 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v1/myelon/conversations.json --prompt-text Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 1200 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v3/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --max-model-len 2560 --device-ids 0,1 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18080 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v3/runner/conversations.json --prompt-text Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 1200 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --max-model-len 2560 --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18081 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_long_v3/myelon/conversations.json --prompt-text Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 1200 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v2/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/prefix_off/cpufold0.5`

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
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/prefix_off/cpufold0.5`

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
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/cpufold0.5`

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

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256d/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18320 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18320 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256d/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 240 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18321 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:18321 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v256d/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 256 --max-tokens 1 --request-timeout-sec 240 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_fixed_prompt_v3/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/prefix_off/cpufold0.5`

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
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/cpufold0.5`

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

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_low_decode_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_low_decode_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18080 --num-clients 16 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 16 --limit-max-tokens 32 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_low_decode_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18081 --num-clients 16 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 16 --limit-max-tokens 32 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix32768/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18260 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18260 --num-clients 1 --max-active-conversations 12 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18261 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 8 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18261 --num-clients 1 --max-active-conversations 12 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 32 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v2/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix32768/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18720 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v2/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18720 --num-clients 8 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18721 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v2/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:18721 --num-clients 8 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-30B-A3B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v3/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix32768/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19120 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v3/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:19120 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19121 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen30ba3b_tp2_server_shared_prefix_rr_control_v3/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --url http://127.0.0.1:19121 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
```

## Qwen/Qwen3-0.6B / server_prefill_stress / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_c1_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/blocking_wait/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 20020 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 1 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:20020 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_c1_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 1 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 20021 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 1 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:20021 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_c1_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 256 --concurrency 1 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_c32_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/blocking_wait/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19820 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19820 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_c32_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19821 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19821 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_c32_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/blocking_wait/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19620 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19620 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19621 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19621 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_nospin_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_spin_c32_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 20120 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:20120 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_spin_c32_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 20121 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:20121 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_spin_c32_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / single_gpu

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19420 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 1 --force-runner --device-ids 0 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19420 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19421 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 1 --myelon-ipc --device-ids 0 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19421 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_singlegpu_fixed_prompt_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_nospin_c32_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/blocking_wait/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19920 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19920 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_nospin_c32_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19921 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19921 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_nospin_c32_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_nospin_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/blocking_wait/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19720 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19720 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_nospin_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19721 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19721 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_nospin_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_spin_c32_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 20220 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:20220 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_spin_c32_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 20221 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:20221 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_spin_c32_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 32 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19520 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19520 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_v1/runner/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 19521 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp python3 /root/Documents/myelon-launch/vllm.rs/scripts/benchmark_server_fixed_prompt_burst.py --url http://127.0.0.1:19521 --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_fixed_prompt_v1/myelon/conversations.json --prompt-text Please talk about China in more details. --num-requests 512 --concurrency 256 --max-tokens 1 --request-timeout-sec 300 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_cache_thrash_rr_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix1024/kv0.08/cpufold0.05`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_cache_thrash_rr_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_cache_thrash_rr_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-0.6B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_shared_prefix_rr_control_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix32768/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_shared_prefix_rr_control_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18080 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_06b_tp2_server_shared_prefix_rr_control_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca --url http://127.0.0.1:18081 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name c1899de289a04d12100db370d81485cdf75e47ca
```

## Qwen/Qwen3-4B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix512/kv0.12/cpufold0.2`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 512 --kv-fraction 0.12 --cpu-mem-fold 0.2
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 16 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 512 --kv-fraction 0.12 --cpu-mem-fold 0.2
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_balanced_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 16 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 600 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-4B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix1024/kv0.08/cpufold0.05`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-4B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v2/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix1024/kv0.08/cpufold0.05`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v2/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 1024 --kv-fraction 0.08 --cpu-mem-fold 0.05
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_cache_thrash_rr_v2/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-4B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_low_decode_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix_off/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_low_decode_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 16 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 300 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 16 --limit-max-tokens 32 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 32 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_stress_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_low_decode_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 16 --max-active-conversations 32 --max-turns 6 --max-retries 1 --request-timeout-sec 300 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 192 --limit-min-tokens 16 --limit-max-tokens 32 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-4B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v1/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix32768/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v1/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v1/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 180 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

## Qwen/Qwen3-4B / server_prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v2/report.json`
- status: `completed`
- artifact_class: `fullpass/benchmark_complete/full_completion`
- transport_settings_profile: `socket_vs_myelon_process_runner/rpc8192/resp8192/busy_spin/prefix32768/kv0.55/cpufold0.5`

### runner

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18080 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v2/runner/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18080 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

### myelon

- server_command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --server --port 18081 --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --max-num-seqs 64 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin --prefix-cache --prefix-cache-max-tokens 32768 --kv-fraction 0.55 --cpu-mem-fold 0.5
```
- benchmark_command:
```bash
uv run --with aiohttp --with numpy --with pandas --with transformers --with tqdm python3 /root/Documents/myelon-launch/vllm/benchmarks/multi_turn/benchmark_serving_multi_turn.py --input-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_benchmarking_2026_04_06/inputs/synthetic_server_prefill_shared_prefix_round_robin.json --output-file /root/Documents/myelon-launch/vllm.rs/artifacts/h100_bridge_campaign_20260406/qwen3_4b_tp2_server_shared_prefix_rr_control_v2/myelon/conversations.json --model /root/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c --url http://127.0.0.1:18081 --num-clients 32 --max-active-conversations 64 --max-turns 6 --max-retries 1 --request-timeout-sec 240 --request-rate 0.0 --conversation-sampling round_robin --max-num-requests 384 --limit-min-tokens 8 --limit-max-tokens 8 --served-model-name 1cfa9a7208912126459214e8b04321603b3df60c
```

