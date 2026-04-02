# TCP Myelon PD First-Transfer Artifact

This directory captures the timed Myelon PD repro on `Qwen/Qwen3-0.6B`.

Configuration:

- transport: `tcp://127.0.0.1:18100`
- mode: `myelon_pd`
- workload: `pd_inputs/pd_transfer_first_request.json`
- requests: `1`
- warmup: disabled

Result:

- the run was intentionally wrapped with `timeout 45s`
- no benchmark report was produced because the process tree never completed
- the preserved evidence is in:
  - `myelon_pd/client_server.log`
  - `myelon_pd/pd_server.log`

Key stop point:

- PD server completes the first Myelon prefill response
- PD server scheduler then requests `KvCacheSend` on the old runner control path
- there is no subsequent `Runner received KvCacheSend ...` log

See also:

- `../pd_debug_notes.md`
- `../workload.md`
