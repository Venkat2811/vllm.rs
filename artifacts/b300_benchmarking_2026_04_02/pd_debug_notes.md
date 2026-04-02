# PD Debug Notes

Date: `2026-04-02`
Host: current Blackwell KVM VM (`2 x RTX PRO 6000 Blackwell`)
Model: `Qwen/Qwen3-0.6B`

## Current PD Execution Model in `vllm.rs`

### PD client request path

1. Scheduler decides a request should be offloaded.
2. `Scheduler::try_transfer()` routes through `BlockManager::try_transfer_prefill()`.
3. In process-runner mode this sends `MessageType::TransferPrefill` over the legacy local socket control channel.
4. The subprocess runner handles `MessageType::TransferPrefill` by calling `ModelRunner::transfer_prefill()`.
5. `ModelRunner::transfer_prefill()` uses the PD `Transfer` subsystem to send `TransferMessage::TransferPrefill` to the PD server over LocalIPC or TCP.

### PD server prefill and KV export path

1. The PD server `Transfer` listener receives `TransferMessage::TransferPrefill`.
2. `Scheduler::schedule()` pulls that pending sequence via `BlockManager::try_receive_prefill()`.
3. The PD server runs model prefill.
4. In `Scheduler::postprocess()`, PD server mode calls `BlockManager::try_send_kvcache()`.
5. In process-runner mode that sends `MessageType::KvCacheSend` over the legacy local socket control channel.
6. The subprocess runner should handle `MessageType::KvCacheSend` by calling `ModelRunner::send_kvcache()`, which uses the PD `Transfer` subsystem to send `TransferMessage::TransferKvCache` back to the client.

## What Myelon Changes Today

When Myelon is enabled in process-runner mode:

1. Engine queues `InitMyelonTransport`.
2. The subprocess runner attaches to the Myelon rings.
3. The subprocess runner then `break`s out of the old local socket loop and enters the Myelon loop.

The Myelon loop currently handles only:

- `RunPrefill`
- `RunDecode`
- `FinishDecode`
- `Cancel`
- `Shutdown`

It does **not** handle:

- `TransferPrefill`
- `ReceivePrefill`
- `CheckPrefillStatus`
- `KvCacheSend`
- `KvCacheReceive`
- `KvCacheRelease`
- `CheckKvCacheRelease`

## Confirmed Current Failure

The preserved `tcp myelon first-transfer` logs show:

1. PD client sends a large request.
2. PD server receives `TransferPrefill`.
3. PD server enables Myelon and finishes the first Myelon prefill.
4. PD server scheduler logs:

`PD Server: seq 0 reached postprocess under Myelon IPC; requesting KvCacheSend over the runner control path.`

After that there is no:

- `Runner received KvCacheSend ...`
- `PD Server: transferred KV cache for seq ...`
- client completion

That is consistent with the code path above: once the runner has switched to the Myelon loop, there is no consumer left for the legacy `KvCacheSend` socket command.

## Separate Transport Finding

LocalIPC PD KV transfer is also blocked on this VM for a different reason:

- `KvCacheReceive failed: Err(cuIpcOpenMemHandle_v2 failed: DriverError(CUDA_ERROR_PEER_ACCESS_UNSUPPORTED, "peer access is not supported between these two devices"))`

So on this host:

- LocalIPC PD control-plane smoke can work
- LocalIPC PD real KV transfer cannot be benchmarked
- TCP PD runner path is valid
- TCP PD Myelon path hangs for the structural reason above

## Immediate Implications

Current Myelon PD on process runners is not just "buggy performance". It is structurally incomplete for the existing PD control/KV-export model.

One of these must happen before PD + Myelon can work in current architecture:

1. Extend the Myelon protocol to support the PD helper verbs, especially `KvCacheSend` and likely `KvCacheReceive` / release-status helpers.
2. Keep the legacy local socket control loop alive alongside the Myelon execution loop.
3. Do not enable Myelon on PD server runners, and only use it where the remaining control path is still compatible.

This is separate from TP inside prefill/decode nodes. TP-within-node may still be viable even if current PD server KV export is not.
