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

Current Myelon PD on process runners was not just "buggy performance". It was structurally incomplete for the existing PD control/KV-export model.

That gap is now fixed on the current branch by extending the Myelon protocol with the PD helper verbs and routing process-runner PD helpers through `MyelonEngineTransport` after Myelon handoff.

## Update After Helper-Verb Extension

Implemented on the current branch:

1. The Myelon protocol now carries:
   - `TransferPrefill`
   - `ReceivePrefill`
   - `CheckPrefillStatus`
   - `KvCacheSend`
   - `KvCacheReceive`
   - `KvCacheRelease`
   - `CheckKvCacheRelease`
2. Once Myelon handoff happens, process-runner PD helpers no longer try to use the abandoned socket loop.
3. The runner-side Myelon loop now executes those helper verbs directly against the existing `ModelRunner` PD methods.

Confirmed result on this host after the extension:

- TCP `myelon_pd` first-transfer fallback now completes end-to-end.
- TCP `myelon_pd` warmed synthetic repeated run now also completes end-to-end.
- PD server logs now show the formerly missing step:
  - `Runner received Myelon KvCacheSend for seq ...`
  - followed by successful KV transfer and client completion
- LocalIPC `myelon_pd` now shows the same control-path fix:
  - PD server reaches `Runner received Myelon KvCacheSend for seq ...`
  - PD server reports successful `KvCacheSend`
  - client receives the KV transfer envelope
  - failure now occurs later at CUDA IPC import on the client:
    - `cuIpcOpenMemHandle_v2 ... CUDA_ERROR_PEER_ACCESS_UNSUPPORTED`

Current status after the fix:

- TCP runner PD: green
- TCP Myelon PD: green on the current `Qwen/Qwen3-0.6B` first-transfer and warmed synthetic slices
- LocalIPC PD control path: fixed
- LocalIPC PD data path: still blocked for real KV transfer on this VM by `CUDA_ERROR_PEER_ACCESS_UNSUPPORTED`

This is still separate from TP inside prefill/decode nodes. TP-within-node may be pursued independently of the LocalIPC PD limitation on this VM.
