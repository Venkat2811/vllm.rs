# All Run Commands

- campaign_root: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406`

## Qwen/Qwen3-30B-A3B / prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_first_prefill_v1/report.json`
- status: `completed`

### runner

- command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 1 --max-model-len 2560 --max-tokens 1 --prompts Please talk about China in more details. --batch 256 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```

### myelon

- command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 1 --max-model-len 2560 --max-tokens 1 --prompts Please talk about China in more details. --batch 256 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```

## Qwen/Qwen3-30B-A3B / prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch128_v1/report.json`
- status: `completed`

### runner

- command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 1 --max-model-len 2560 --max-tokens 1 --prompts Please talk about China in more details. --batch 128 --dtype bf16 --seed 123 --num-shards 2 --force-runner --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```

### myelon

- command:
```bash
/root/Documents/myelon-launch/vllm.rs/target/release/vllm-rs --w /root/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 --max-num-seqs 1 --max-model-len 2560 --max-tokens 1 --prompts Please talk about China in more details. --batch 128 --dtype bf16 --seed 123 --num-shards 2 --myelon-ipc --device-ids 0,1 --myelon-rpc-depth 8192 --myelon-response-depth 8192 --myelon-busy-spin
```

## Qwen/Qwen3-30B-A3B / prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_batch256_v2/report.json`
- status: `warmup_incomplete_metrics`

## Qwen/Qwen3-30B-A3B / prefill_stress / tp2

- report_json: `/root/Documents/myelon-launch/vllm.rs/artifacts/h100_prefill_campaign_20260406/qwen30ba3b_tp2_min_decode_v1/report.json`
- status: `warmup_incomplete_metrics`

