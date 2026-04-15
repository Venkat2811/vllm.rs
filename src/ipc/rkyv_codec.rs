//! rkyv-based zero-copy serialization for Myelon IPC messages.
//! Enabled by the `myelon-rkyv` feature flag.
#![cfg(feature = "myelon-rkyv")]

use crate::core::sequence::{DecodeSequence, Sequence};
use crate::ipc::myelon_ipc::{MsgKind, MyelonRequest, MyelonResponse};
use candle_core::Result as CandleResult;
use std::collections::HashMap;

fn rkyv_err(e: impl std::fmt::Display) -> candle_core::Error {
    candle_core::Error::Msg(format!("rkyv: {e}"))
}

// --- Request encode ---

pub fn encode_request(req: &MyelonRequest) -> CandleResult<Vec<u8>> {
    match req {
        MyelonRequest::RunPrefill { sequences } => rkyv::to_bytes::<rkyv::rancor::Error>(sequences)
            .map(|v| v.to_vec())
            .map_err(rkyv_err),
        MyelonRequest::RunDecode { sequences } => rkyv::to_bytes::<rkyv::rancor::Error>(sequences)
            .map(|v| v.to_vec())
            .map_err(rkyv_err),
        MyelonRequest::FinishDecode { sequence_id }
        | MyelonRequest::Cancel { sequence_id }
        | MyelonRequest::CheckPrefillStatus { sequence_id }
        | MyelonRequest::KvCacheRelease { sequence_id }
        | MyelonRequest::CheckKvCacheRelease { sequence_id } => {
            rkyv::to_bytes::<rkyv::rancor::Error>(sequence_id)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonRequest::TransferPrefill { sequence } | MyelonRequest::KvCacheReceive { sequence } => {
            rkyv::to_bytes::<rkyv::rancor::Error>(sequence)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonRequest::ReceivePrefill { available_tokens } => {
            rkyv::to_bytes::<rkyv::rancor::Error>(available_tokens)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonRequest::KvCacheSend {
            sequence,
            first_token,
        } => {
            let payload = (sequence.clone(), *first_token);
            rkyv::to_bytes::<rkyv::rancor::Error>(&payload)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonRequest::KvCacheSwap { mappings, swap_in } => {
            // HashMap doesn't derive Archive by default in rkyv 0.8 without hashbrown feature.
            // Serialize as (Vec<usize>, Vec<usize>, bool) instead.
            let keys: Vec<usize> = mappings.keys().copied().collect();
            let values: Vec<usize> = mappings.values().copied().collect();
            let payload = (keys, values, *swap_in);
            rkyv::to_bytes::<rkyv::rancor::Error>(&payload)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonRequest::Shutdown => Ok(Vec::new()),
    }
}

// --- Request decode ---

pub fn decode_request(kind: u8, payload: &[u8]) -> CandleResult<MyelonRequest> {
    let msg_kind = MsgKind::from_u8(kind)?;
    match msg_kind {
        MsgKind::RunPrefill => {
            let archived =
                rkyv::access::<rkyv::Archived<Vec<Sequence>>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let sequences: Vec<Sequence> =
                rkyv::deserialize::<Vec<Sequence>, rkyv::rancor::Error>(archived)
                    .map_err(rkyv_err)?;
            Ok(MyelonRequest::RunPrefill { sequences })
        }
        MsgKind::RunDecode => {
            let archived =
                rkyv::access::<rkyv::Archived<Vec<DecodeSequence>>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let sequences: Vec<DecodeSequence> =
                rkyv::deserialize::<Vec<DecodeSequence>, rkyv::rancor::Error>(archived)
                    .map_err(rkyv_err)?;
            Ok(MyelonRequest::RunDecode { sequences })
        }
        MsgKind::FinishDecode => {
            let archived =
                rkyv::access::<rkyv::Archived<usize>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let sequence_id: usize =
                rkyv::deserialize::<usize, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonRequest::FinishDecode { sequence_id })
        }
        MsgKind::Cancel => {
            let archived =
                rkyv::access::<rkyv::Archived<usize>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let sequence_id: usize =
                rkyv::deserialize::<usize, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonRequest::Cancel { sequence_id })
        }
        MsgKind::TransferPrefill => {
            let archived =
                rkyv::access::<rkyv::Archived<Sequence>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let sequence: Sequence =
                rkyv::deserialize::<Sequence, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonRequest::TransferPrefill { sequence })
        }
        MsgKind::ReceivePrefill => {
            let archived =
                rkyv::access::<rkyv::Archived<usize>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let available_tokens: usize =
                rkyv::deserialize::<usize, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonRequest::ReceivePrefill { available_tokens })
        }
        MsgKind::CheckPrefillStatus
        | MsgKind::KvCacheRelease
        | MsgKind::CheckKvCacheRelease => {
            let archived =
                rkyv::access::<rkyv::Archived<usize>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let sequence_id: usize =
                rkyv::deserialize::<usize, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            match msg_kind {
                MsgKind::CheckPrefillStatus => Ok(MyelonRequest::CheckPrefillStatus { sequence_id }),
                MsgKind::KvCacheRelease => Ok(MyelonRequest::KvCacheRelease { sequence_id }),
                MsgKind::CheckKvCacheRelease => {
                    Ok(MyelonRequest::CheckKvCacheRelease { sequence_id })
                }
                _ => unreachable!(),
            }
        }
        MsgKind::KvCacheSend => {
            let archived = rkyv::access::<
                rkyv::Archived<(Sequence, u32)>,
                rkyv::rancor::Error,
            >(payload)
            .map_err(rkyv_err)?;
            let (sequence, first_token): (Sequence, u32) =
                rkyv::deserialize::<(Sequence, u32), rkyv::rancor::Error>(archived)
                    .map_err(rkyv_err)?;
            Ok(MyelonRequest::KvCacheSend {
                sequence,
                first_token,
            })
        }
        MsgKind::KvCacheReceive => {
            let archived =
                rkyv::access::<rkyv::Archived<Sequence>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let sequence: Sequence =
                rkyv::deserialize::<Sequence, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonRequest::KvCacheReceive { sequence })
        }
        MsgKind::KvCacheSwap => {
            let archived = rkyv::access::<
                rkyv::Archived<(Vec<usize>, Vec<usize>, bool)>,
                rkyv::rancor::Error,
            >(payload)
            .map_err(rkyv_err)?;
            let (keys, values, swap_in): (Vec<usize>, Vec<usize>, bool) = rkyv::deserialize::<
                (Vec<usize>, Vec<usize>, bool),
                rkyv::rancor::Error,
            >(archived)
            .map_err(rkyv_err)?;
            let mappings: HashMap<usize, usize> = keys.into_iter().zip(values).collect();
            Ok(MyelonRequest::KvCacheSwap { mappings, swap_in })
        }
        MsgKind::Shutdown => {
            if !payload.is_empty() {
                candle_core::bail!("Shutdown request must not carry a payload");
            }
            Ok(MyelonRequest::Shutdown)
        }
        _ => {
            candle_core::bail!("response kind {} is not a request", kind);
        }
    }
}

// --- Response encode ---

pub fn encode_response(resp: &MyelonResponse) -> CandleResult<Vec<u8>> {
    match resp {
        MyelonResponse::RunResponse(output_ids) => {
            rkyv::to_bytes::<rkyv::rancor::Error>(output_ids)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonResponse::TransferPrefillResponse(v)
        | MyelonResponse::CheckPrefillStatusResponse(v)
        | MyelonResponse::KvCacheSendResponse(v)
        | MyelonResponse::KvCacheReleaseResponse(v)
        | MyelonResponse::CheckKvCacheReleaseResponse(v)
        | MyelonResponse::KvCacheSwapResponse(v) => rkyv::to_bytes::<rkyv::rancor::Error>(v)
            .map(|v| v.to_vec())
            .map_err(rkyv_err),
        MyelonResponse::ReceivePrefillResponse(v) => {
            rkyv::to_bytes::<rkyv::rancor::Error>(v)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonResponse::KvCacheReceiveResponse(v) => {
            rkyv::to_bytes::<rkyv::rancor::Error>(v)
                .map(|v| v.to_vec())
                .map_err(rkyv_err)
        }
        MyelonResponse::Error(error) => Ok(error.as_bytes().to_vec()),
    }
}

// --- Response decode ---

pub fn decode_response(kind: u8, payload: &[u8]) -> CandleResult<MyelonResponse> {
    match MsgKind::from_u8(kind)? {
        MsgKind::RunResponse => {
            let archived =
                rkyv::access::<rkyv::Archived<Vec<u32>>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let output_ids: Vec<u32> =
                rkyv::deserialize::<Vec<u32>, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonResponse::RunResponse(output_ids))
        }
        MsgKind::TransferPrefillResponse => {
            let archived =
                rkyv::access::<rkyv::Archived<bool>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let v: bool =
                rkyv::deserialize::<bool, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonResponse::TransferPrefillResponse(v))
        }
        MsgKind::ReceivePrefillResponse => {
            let archived = rkyv::access::<
                rkyv::Archived<(bool, Option<Sequence>)>,
                rkyv::rancor::Error,
            >(payload)
            .map_err(rkyv_err)?;
            let v: (bool, Option<Sequence>) =
                rkyv::deserialize::<(bool, Option<Sequence>), rkyv::rancor::Error>(archived)
                    .map_err(rkyv_err)?;
            Ok(MyelonResponse::ReceivePrefillResponse(v))
        }
        MsgKind::CheckPrefillStatusResponse => {
            let archived =
                rkyv::access::<rkyv::Archived<bool>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let v: bool =
                rkyv::deserialize::<bool, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonResponse::CheckPrefillStatusResponse(v))
        }
        MsgKind::KvCacheSendResponse => {
            let archived =
                rkyv::access::<rkyv::Archived<bool>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let v: bool =
                rkyv::deserialize::<bool, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonResponse::KvCacheSendResponse(v))
        }
        MsgKind::KvCacheReceiveResponse => {
            let archived = rkyv::access::<
                rkyv::Archived<(bool, u32, usize)>,
                rkyv::rancor::Error,
            >(payload)
            .map_err(rkyv_err)?;
            let v: (bool, u32, usize) =
                rkyv::deserialize::<(bool, u32, usize), rkyv::rancor::Error>(archived)
                    .map_err(rkyv_err)?;
            Ok(MyelonResponse::KvCacheReceiveResponse(v))
        }
        MsgKind::KvCacheReleaseResponse => {
            let archived =
                rkyv::access::<rkyv::Archived<bool>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let v: bool =
                rkyv::deserialize::<bool, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonResponse::KvCacheReleaseResponse(v))
        }
        MsgKind::CheckKvCacheReleaseResponse => {
            let archived =
                rkyv::access::<rkyv::Archived<bool>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let v: bool =
                rkyv::deserialize::<bool, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonResponse::CheckKvCacheReleaseResponse(v))
        }
        MsgKind::KvCacheSwapResponse => {
            let archived =
                rkyv::access::<rkyv::Archived<bool>, rkyv::rancor::Error>(payload)
                    .map_err(rkyv_err)?;
            let v: bool =
                rkyv::deserialize::<bool, rkyv::rancor::Error>(archived).map_err(rkyv_err)?;
            Ok(MyelonResponse::KvCacheSwapResponse(v))
        }
        MsgKind::Error => Ok(MyelonResponse::Error(
            String::from_utf8_lossy(payload).into_owned(),
        )),
        _ => {
            candle_core::bail!("request kind {} is not a response", kind);
        }
    }
}
