//! rkyv-based zero-copy serialization for Myelon IPC messages.
//! Enabled by the `codec-rkyv` feature flag.
#![cfg(feature = "codec-rkyv")]

use crate::core::sequence::{DecodeSequence, Sequence};
use crate::ipc::myelon_ipc::{MsgKind, MyelonRequest, MyelonResponse};
use candle_core::Result as CandleResult;
use std::collections::HashMap;

fn rkyv_err(e: impl std::fmt::Display) -> candle_core::Error {
    candle_core::Error::Msg(format!("rkyv: {e}"))
}

macro_rules! decode_owned {
    ($ty:ty, $payload:expr) => {{
        let payload = $payload;
        if (payload.as_ptr() as usize) % rkyv::util::AlignedVec::<16>::ALIGNMENT == 0 {
            rkyv::from_bytes::<$ty, rkyv::rancor::Error>(payload).map_err(rkyv_err)?
        } else {
            let mut aligned = rkyv::util::AlignedVec::<16>::with_capacity(payload.len());
            aligned.extend_from_slice(payload);
            rkyv::from_bytes::<$ty, rkyv::rancor::Error>(&aligned).map_err(rkyv_err)?
        }
    }};
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
        MsgKind::RunPrefill => Ok(MyelonRequest::RunPrefill {
            sequences: decode_owned!(Vec<Sequence>, payload),
        }),
        MsgKind::RunDecode => Ok(MyelonRequest::RunDecode {
            sequences: decode_owned!(Vec<DecodeSequence>, payload),
        }),
        MsgKind::FinishDecode => Ok(MyelonRequest::FinishDecode {
            sequence_id: decode_owned!(usize, payload),
        }),
        MsgKind::Cancel => Ok(MyelonRequest::Cancel {
            sequence_id: decode_owned!(usize, payload),
        }),
        MsgKind::TransferPrefill => Ok(MyelonRequest::TransferPrefill {
            sequence: decode_owned!(Sequence, payload),
        }),
        MsgKind::ReceivePrefill => Ok(MyelonRequest::ReceivePrefill {
            available_tokens: decode_owned!(usize, payload),
        }),
        MsgKind::CheckPrefillStatus
        | MsgKind::KvCacheRelease
        | MsgKind::CheckKvCacheRelease => {
            let sequence_id: usize = decode_owned!(usize, payload);
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
            let (sequence, first_token): (Sequence, u32) =
                decode_owned!((Sequence, u32), payload);
            Ok(MyelonRequest::KvCacheSend {
                sequence,
                first_token,
            })
        }
        MsgKind::KvCacheReceive => Ok(MyelonRequest::KvCacheReceive {
            sequence: decode_owned!(Sequence, payload),
        }),
        MsgKind::KvCacheSwap => {
            let (keys, values, swap_in): (Vec<usize>, Vec<usize>, bool) =
                decode_owned!((Vec<usize>, Vec<usize>, bool), payload);
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
        MsgKind::RunResponse => Ok(MyelonResponse::RunResponse(decode_owned!(Vec<u32>, payload))),
        MsgKind::TransferPrefillResponse => Ok(MyelonResponse::TransferPrefillResponse(
            decode_owned!(bool, payload),
        )),
        MsgKind::ReceivePrefillResponse => Ok(MyelonResponse::ReceivePrefillResponse(
            decode_owned!((bool, Option<Sequence>), payload),
        )),
        MsgKind::CheckPrefillStatusResponse => Ok(MyelonResponse::CheckPrefillStatusResponse(
            decode_owned!(bool, payload),
        )),
        MsgKind::KvCacheSendResponse => Ok(MyelonResponse::KvCacheSendResponse(
            decode_owned!(bool, payload),
        )),
        MsgKind::KvCacheReceiveResponse => Ok(MyelonResponse::KvCacheReceiveResponse(
            decode_owned!((bool, u32, usize), payload),
        )),
        MsgKind::KvCacheReleaseResponse => Ok(MyelonResponse::KvCacheReleaseResponse(
            decode_owned!(bool, payload),
        )),
        MsgKind::CheckKvCacheReleaseResponse => Ok(MyelonResponse::CheckKvCacheReleaseResponse(
            decode_owned!(bool, payload),
        )),
        MsgKind::KvCacheSwapResponse => Ok(MyelonResponse::KvCacheSwapResponse(
            decode_owned!(bool, payload),
        )),
        MsgKind::Error => Ok(MyelonResponse::Error(
            String::from_utf8_lossy(payload).into_owned(),
        )),
        _ => {
            candle_core::bail!("request kind {} is not a response", kind);
        }
    }
}
