use crate::ipc::myelon_ipc::{MsgKind, MyelonRequest, MyelonResponse};
use myelon_playground::codec::ZeroCopyCodec;
use myelon_playground::{Codec, CodecError};

pub const MYELON_TYPED_ENVELOPE_HEADER_BYTES: usize = 16;

#[derive(Debug, Clone)]
pub struct TypedMyelonRequest(pub MyelonRequest);

impl TypedMyelonRequest {
    pub fn into_inner(self) -> MyelonRequest {
        self.0
    }
}

#[derive(Debug, Clone)]
pub struct TypedMyelonResponse(pub MyelonResponse);

impl TypedMyelonResponse {
    pub fn into_inner(self) -> MyelonResponse {
        self.0
    }
}

fn encode_envelope(tag: u8, payload: &[u8]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(MYELON_TYPED_ENVELOPE_HEADER_BYTES + payload.len());
    bytes.push(tag);
    bytes.resize(MYELON_TYPED_ENVELOPE_HEADER_BYTES, 0);
    bytes.extend_from_slice(payload);
    bytes
}

fn decode_envelope(bytes: &[u8]) -> Result<(u8, &[u8]), CodecError> {
    if bytes.len() < MYELON_TYPED_ENVELOPE_HEADER_BYTES {
        return Err(CodecError::decode(format!(
            "typed Myelon envelope too short: {}",
            bytes.len()
        )));
    }
    Ok((bytes[0], &bytes[MYELON_TYPED_ENVELOPE_HEADER_BYTES..]))
}

#[cfg(feature = "codec-rkyv")]
mod typed_rkyv {
    use super::*;
    use crate::core::sequence::{DecodeSequence, Sequence};

    fn access_archived<T>(bytes: &[u8]) -> Result<&T, CodecError>
    where
        T: rkyv::Portable,
    {
        Ok(unsafe { rkyv::access_unchecked::<T>(bytes) })
    }

    pub enum BorrowedTypedMyelonRequest<'a> {
        RunPrefill {
            payload: &'a [u8],
            sequences: &'a rkyv::Archived<Vec<Sequence>>,
        },
        RunDecode {
            payload: &'a [u8],
            sequences: &'a rkyv::Archived<Vec<DecodeSequence>>,
        },
        FinishDecode {
            payload: &'a [u8],
            sequence_id: usize,
        },
        Cancel {
            payload: &'a [u8],
            sequence_id: usize,
        },
        TransferPrefill {
            payload: &'a [u8],
            sequence: &'a rkyv::Archived<Sequence>,
        },
        ReceivePrefill {
            payload: &'a [u8],
            available_tokens: usize,
        },
        CheckPrefillStatus {
            payload: &'a [u8],
            sequence_id: usize,
        },
        KvCacheSend {
            payload: &'a [u8],
            sequence: &'a rkyv::Archived<Sequence>,
            first_token: u32,
        },
        KvCacheReceive {
            payload: &'a [u8],
            sequence: &'a rkyv::Archived<Sequence>,
        },
        KvCacheRelease {
            payload: &'a [u8],
            sequence_id: usize,
        },
        CheckKvCacheRelease {
            payload: &'a [u8],
            sequence_id: usize,
        },
        KvCacheSwap {
            payload: &'a [u8],
            mapping_keys: &'a rkyv::Archived<Vec<usize>>,
            mapping_values: &'a rkyv::Archived<Vec<usize>>,
            swap_in: bool,
        },
        Shutdown,
    }

    impl<'a> BorrowedTypedMyelonRequest<'a> {
        pub fn kind(&self) -> MsgKind {
            match self {
                Self::RunPrefill { .. } => MsgKind::RunPrefill,
                Self::RunDecode { .. } => MsgKind::RunDecode,
                Self::FinishDecode { .. } => MsgKind::FinishDecode,
                Self::Cancel { .. } => MsgKind::Cancel,
                Self::TransferPrefill { .. } => MsgKind::TransferPrefill,
                Self::ReceivePrefill { .. } => MsgKind::ReceivePrefill,
                Self::CheckPrefillStatus { .. } => MsgKind::CheckPrefillStatus,
                Self::KvCacheSend { .. } => MsgKind::KvCacheSend,
                Self::KvCacheReceive { .. } => MsgKind::KvCacheReceive,
                Self::KvCacheRelease { .. } => MsgKind::KvCacheRelease,
                Self::CheckKvCacheRelease { .. } => MsgKind::CheckKvCacheRelease,
                Self::KvCacheSwap { .. } => MsgKind::KvCacheSwap,
                Self::Shutdown => MsgKind::Shutdown,
            }
        }

        pub fn to_owned(&self) -> Result<MyelonRequest, CodecError> {
            match self {
                Self::Shutdown => MyelonRequest::decode(MsgKind::Shutdown.as_u8(), &[]),
                Self::RunPrefill { payload, .. }
                | Self::RunDecode { payload, .. }
                | Self::FinishDecode { payload, .. }
                | Self::Cancel { payload, .. }
                | Self::TransferPrefill { payload, .. }
                | Self::ReceivePrefill { payload, .. }
                | Self::CheckPrefillStatus { payload, .. }
                | Self::KvCacheSend { payload, .. }
                | Self::KvCacheReceive { payload, .. }
                | Self::KvCacheRelease { payload, .. }
                | Self::CheckKvCacheRelease { payload, .. }
                | Self::KvCacheSwap { payload, .. } => {
                    MyelonRequest::decode(self.kind().as_u8(), payload)
                }
            }
            .map_err(CodecError::decode)
        }

        fn from_payload(tag: u8, payload: &'a [u8]) -> Result<Self, CodecError> {
            match MsgKind::from_u8(tag).map_err(CodecError::decode)? {
                MsgKind::RunPrefill => Ok(Self::RunPrefill {
                    payload,
                    sequences: access_archived::<rkyv::Archived<Vec<Sequence>>>(payload)?,
                }),
                MsgKind::RunDecode => Ok(Self::RunDecode {
                    payload,
                    sequences: access_archived::<rkyv::Archived<Vec<DecodeSequence>>>(payload)?,
                }),
                MsgKind::FinishDecode => Ok(Self::FinishDecode {
                    payload,
                    sequence_id: access_archived::<rkyv::Archived<usize>>(payload)?.to_native()
                        as usize,
                }),
                MsgKind::Cancel => Ok(Self::Cancel {
                    payload,
                    sequence_id: access_archived::<rkyv::Archived<usize>>(payload)?.to_native()
                        as usize,
                }),
                MsgKind::TransferPrefill => Ok(Self::TransferPrefill {
                    payload,
                    sequence: access_archived::<rkyv::Archived<Sequence>>(payload)?,
                }),
                MsgKind::ReceivePrefill => Ok(Self::ReceivePrefill {
                    payload,
                    available_tokens: access_archived::<rkyv::Archived<usize>>(payload)?
                        .to_native() as usize,
                }),
                MsgKind::CheckPrefillStatus => Ok(Self::CheckPrefillStatus {
                    payload,
                    sequence_id: access_archived::<rkyv::Archived<usize>>(payload)?.to_native()
                        as usize,
                }),
                MsgKind::KvCacheSend => {
                    let archived =
                        access_archived::<rkyv::Archived<(Sequence, u32)>>(payload)?;
                    Ok(Self::KvCacheSend {
                        payload,
                        sequence: &archived.0,
                        first_token: archived.1.to_native(),
                    })
                }
                MsgKind::KvCacheReceive => Ok(Self::KvCacheReceive {
                    payload,
                    sequence: access_archived::<rkyv::Archived<Sequence>>(payload)?,
                }),
                MsgKind::KvCacheRelease => Ok(Self::KvCacheRelease {
                    payload,
                    sequence_id: access_archived::<rkyv::Archived<usize>>(payload)?.to_native()
                        as usize,
                }),
                MsgKind::CheckKvCacheRelease => Ok(Self::CheckKvCacheRelease {
                    payload,
                    sequence_id: access_archived::<rkyv::Archived<usize>>(payload)?.to_native()
                        as usize,
                }),
                MsgKind::KvCacheSwap => {
                    let archived = access_archived::<
                        rkyv::Archived<(Vec<usize>, Vec<usize>, bool)>,
                    >(payload)?;
                    Ok(Self::KvCacheSwap {
                        payload,
                        mapping_keys: &archived.0,
                        mapping_values: &archived.1,
                        swap_in: archived.2,
                    })
                }
                MsgKind::Shutdown => Ok(Self::Shutdown),
                other => Err(CodecError::decode(format!(
                    "response kind {:?} is not a typed request payload",
                    other
                ))),
            }
        }
    }

    pub enum BorrowedTypedMyelonResponse<'a> {
        RunResponse {
            payload: &'a [u8],
            output_ids: &'a rkyv::Archived<Vec<u32>>,
        },
        TransferPrefillResponse {
            payload: &'a [u8],
            value: bool,
        },
        ReceivePrefillResponse {
            payload: &'a [u8],
            value: &'a rkyv::Archived<(bool, Option<Sequence>)>,
        },
        CheckPrefillStatusResponse {
            payload: &'a [u8],
            value: bool,
        },
        KvCacheSendResponse {
            payload: &'a [u8],
            value: bool,
        },
        KvCacheReceiveResponse {
            payload: &'a [u8],
            value: &'a rkyv::Archived<(bool, u32, usize)>,
        },
        KvCacheReleaseResponse {
            payload: &'a [u8],
            value: bool,
        },
        CheckKvCacheReleaseResponse {
            payload: &'a [u8],
            value: bool,
        },
        KvCacheSwapResponse {
            payload: &'a [u8],
            value: bool,
        },
        Error {
            payload: &'a [u8],
            message: String,
        },
    }

    impl<'a> BorrowedTypedMyelonResponse<'a> {
        pub fn kind(&self) -> MsgKind {
            match self {
                Self::RunResponse { .. } => MsgKind::RunResponse,
                Self::TransferPrefillResponse { .. } => MsgKind::TransferPrefillResponse,
                Self::ReceivePrefillResponse { .. } => MsgKind::ReceivePrefillResponse,
                Self::CheckPrefillStatusResponse { .. } => MsgKind::CheckPrefillStatusResponse,
                Self::KvCacheSendResponse { .. } => MsgKind::KvCacheSendResponse,
                Self::KvCacheReceiveResponse { .. } => MsgKind::KvCacheReceiveResponse,
                Self::KvCacheReleaseResponse { .. } => MsgKind::KvCacheReleaseResponse,
                Self::CheckKvCacheReleaseResponse { .. } => {
                    MsgKind::CheckKvCacheReleaseResponse
                }
                Self::KvCacheSwapResponse { .. } => MsgKind::KvCacheSwapResponse,
                Self::Error { .. } => MsgKind::Error,
            }
        }

        pub fn to_owned(&self) -> Result<MyelonResponse, CodecError> {
            let payload = match self {
                Self::RunResponse { payload, .. }
                | Self::TransferPrefillResponse { payload, .. }
                | Self::ReceivePrefillResponse { payload, .. }
                | Self::CheckPrefillStatusResponse { payload, .. }
                | Self::KvCacheSendResponse { payload, .. }
                | Self::KvCacheReceiveResponse { payload, .. }
                | Self::KvCacheReleaseResponse { payload, .. }
                | Self::CheckKvCacheReleaseResponse { payload, .. }
                | Self::KvCacheSwapResponse { payload, .. }
                | Self::Error { payload, .. } => *payload,
            };
            MyelonResponse::decode(self.kind().as_u8(), payload).map_err(CodecError::decode)
        }

        fn from_payload(tag: u8, payload: &'a [u8]) -> Result<Self, CodecError> {
            match MsgKind::from_u8(tag).map_err(CodecError::decode)? {
                MsgKind::RunResponse => Ok(Self::RunResponse {
                    payload,
                    output_ids: access_archived::<rkyv::Archived<Vec<u32>>>(payload)?,
                }),
                MsgKind::TransferPrefillResponse => Ok(Self::TransferPrefillResponse {
                    payload,
                    value: *access_archived::<rkyv::Archived<bool>>(payload)?,
                }),
                MsgKind::ReceivePrefillResponse => Ok(Self::ReceivePrefillResponse {
                    payload,
                    value: access_archived::<rkyv::Archived<(bool, Option<Sequence>)>>(payload)?,
                }),
                MsgKind::CheckPrefillStatusResponse => {
                    Ok(Self::CheckPrefillStatusResponse {
                        payload,
                        value: *access_archived::<rkyv::Archived<bool>>(payload)?,
                    })
                }
                MsgKind::KvCacheSendResponse => Ok(Self::KvCacheSendResponse {
                    payload,
                    value: *access_archived::<rkyv::Archived<bool>>(payload)?,
                }),
                MsgKind::KvCacheReceiveResponse => Ok(Self::KvCacheReceiveResponse {
                    payload,
                    value: access_archived::<rkyv::Archived<(bool, u32, usize)>>(payload)?,
                }),
                MsgKind::KvCacheReleaseResponse => Ok(Self::KvCacheReleaseResponse {
                    payload,
                    value: *access_archived::<rkyv::Archived<bool>>(payload)?,
                }),
                MsgKind::CheckKvCacheReleaseResponse => {
                    Ok(Self::CheckKvCacheReleaseResponse {
                        payload,
                        value: *access_archived::<rkyv::Archived<bool>>(payload)?,
                    })
                }
                MsgKind::KvCacheSwapResponse => Ok(Self::KvCacheSwapResponse {
                    payload,
                    value: *access_archived::<rkyv::Archived<bool>>(payload)?,
                }),
                MsgKind::Error => Ok(Self::Error {
                    payload,
                    message: String::from_utf8_lossy(payload).into_owned(),
                }),
                other => Err(CodecError::decode(format!(
                    "request kind {:?} is not a typed response payload",
                    other
                ))),
            }
        }
    }

    impl ZeroCopyCodec for TypedMyelonRequest {
        type Archived<'a> = BorrowedTypedMyelonRequest<'a>;

        fn access<'a>(bytes: &'a [u8]) -> Result<Self::Archived<'a>, CodecError> {
            let (tag, payload) = decode_envelope(bytes)?;
            BorrowedTypedMyelonRequest::from_payload(tag, payload)
        }
    }

    impl ZeroCopyCodec for TypedMyelonResponse {
        type Archived<'a> = BorrowedTypedMyelonResponse<'a>;

        fn access<'a>(bytes: &'a [u8]) -> Result<Self::Archived<'a>, CodecError> {
            let (tag, payload) = decode_envelope(bytes)?;
            BorrowedTypedMyelonResponse::from_payload(tag, payload)
        }
    }
}

#[cfg(feature = "codec-rkyv")]
pub use typed_rkyv::{BorrowedTypedMyelonRequest, BorrowedTypedMyelonResponse};

#[cfg(all(not(feature = "codec-rkyv"), feature = "codec-flatbuf"))]
mod typed_flatbuf {
    use super::*;
    use crate::ipc::schema;

    #[derive(Debug)]
    pub enum BorrowedTypedMyelonRequest<'a> {
        RunPrefill {
            payload: &'a [u8],
            fb: schema::RunPrefillPayload<'a>,
        },
        RunDecode {
            payload: &'a [u8],
            fb: schema::RunDecodePayload<'a>,
        },
        FinishDecode {
            payload: &'a [u8],
            sequence_id: usize,
        },
        Cancel {
            payload: &'a [u8],
            sequence_id: usize,
        },
        TransferPrefill {
            payload: &'a [u8],
            fb: schema::SingleSequencePayload<'a>,
        },
        ReceivePrefill {
            payload: &'a [u8],
            available_tokens: usize,
        },
        CheckPrefillStatus {
            payload: &'a [u8],
            sequence_id: usize,
        },
        KvCacheSend {
            payload: &'a [u8],
            fb: schema::KvCacheSendPayload<'a>,
        },
        KvCacheReceive {
            payload: &'a [u8],
            fb: schema::SingleSequencePayload<'a>,
        },
        KvCacheRelease {
            payload: &'a [u8],
            sequence_id: usize,
        },
        CheckKvCacheRelease {
            payload: &'a [u8],
            sequence_id: usize,
        },
        KvCacheSwap {
            payload: &'a [u8],
            fb: schema::KvCacheSwapPayload<'a>,
        },
        Shutdown,
    }

    impl<'a> BorrowedTypedMyelonRequest<'a> {
        pub fn kind(&self) -> MsgKind {
            match self {
                Self::RunPrefill { .. } => MsgKind::RunPrefill,
                Self::RunDecode { .. } => MsgKind::RunDecode,
                Self::FinishDecode { .. } => MsgKind::FinishDecode,
                Self::Cancel { .. } => MsgKind::Cancel,
                Self::TransferPrefill { .. } => MsgKind::TransferPrefill,
                Self::ReceivePrefill { .. } => MsgKind::ReceivePrefill,
                Self::CheckPrefillStatus { .. } => MsgKind::CheckPrefillStatus,
                Self::KvCacheSend { .. } => MsgKind::KvCacheSend,
                Self::KvCacheReceive { .. } => MsgKind::KvCacheReceive,
                Self::KvCacheRelease { .. } => MsgKind::KvCacheRelease,
                Self::CheckKvCacheRelease { .. } => MsgKind::CheckKvCacheRelease,
                Self::KvCacheSwap { .. } => MsgKind::KvCacheSwap,
                Self::Shutdown => MsgKind::Shutdown,
            }
        }

        pub fn to_owned(&self) -> Result<MyelonRequest, CodecError> {
            match self {
                Self::Shutdown => MyelonRequest::decode(MsgKind::Shutdown.as_u8(), &[]),
                Self::RunPrefill { payload, .. }
                | Self::RunDecode { payload, .. }
                | Self::FinishDecode { payload, .. }
                | Self::Cancel { payload, .. }
                | Self::TransferPrefill { payload, .. }
                | Self::ReceivePrefill { payload, .. }
                | Self::CheckPrefillStatus { payload, .. }
                | Self::KvCacheSend { payload, .. }
                | Self::KvCacheReceive { payload, .. }
                | Self::KvCacheRelease { payload, .. }
                | Self::CheckKvCacheRelease { payload, .. }
                | Self::KvCacheSwap { payload, .. } => {
                    MyelonRequest::decode(self.kind().as_u8(), payload)
                }
            }
            .map_err(CodecError::decode)
        }

        fn from_payload(tag: u8, payload: &'a [u8]) -> Result<Self, CodecError> {
            match MsgKind::from_u8(tag).map_err(CodecError::decode)? {
                MsgKind::RunPrefill => Ok(Self::RunPrefill {
                    payload,
                    fb: flatbuffers::root::<schema::RunPrefillPayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::RunDecode => Ok(Self::RunDecode {
                    payload,
                    fb: flatbuffers::root::<schema::RunDecodePayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::FinishDecode => {
                    let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::FinishDecode {
                        payload,
                        sequence_id: fb.sequence_id() as usize,
                    })
                }
                MsgKind::Cancel => {
                    let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::Cancel {
                        payload,
                        sequence_id: fb.sequence_id() as usize,
                    })
                }
                MsgKind::TransferPrefill => Ok(Self::TransferPrefill {
                    payload,
                    fb: flatbuffers::root::<schema::SingleSequencePayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::ReceivePrefill => {
                    let fb = flatbuffers::root::<schema::AvailableTokensPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::ReceivePrefill {
                        payload,
                        available_tokens: fb.available_tokens() as usize,
                    })
                }
                MsgKind::CheckPrefillStatus => {
                    let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::CheckPrefillStatus {
                        payload,
                        sequence_id: fb.sequence_id() as usize,
                    })
                }
                MsgKind::KvCacheSend => Ok(Self::KvCacheSend {
                    payload,
                    fb: flatbuffers::root::<schema::KvCacheSendPayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::KvCacheReceive => Ok(Self::KvCacheReceive {
                    payload,
                    fb: flatbuffers::root::<schema::SingleSequencePayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::KvCacheRelease => {
                    let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::KvCacheRelease {
                        payload,
                        sequence_id: fb.sequence_id() as usize,
                    })
                }
                MsgKind::CheckKvCacheRelease => {
                    let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::CheckKvCacheRelease {
                        payload,
                        sequence_id: fb.sequence_id() as usize,
                    })
                }
                MsgKind::KvCacheSwap => Ok(Self::KvCacheSwap {
                    payload,
                    fb: flatbuffers::root::<schema::KvCacheSwapPayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::Shutdown => Ok(Self::Shutdown),
                other => Err(CodecError::decode(format!(
                    "response kind {:?} is not a typed request payload",
                    other
                ))),
            }
        }
    }

    #[derive(Debug)]
    pub enum BorrowedTypedMyelonResponse<'a> {
        RunResponse {
            payload: &'a [u8],
            fb: schema::RunResponsePayload<'a>,
        },
        TransferPrefillResponse {
            payload: &'a [u8],
            value: bool,
        },
        ReceivePrefillResponse {
            payload: &'a [u8],
            fb: schema::ReceivePrefillResponsePayload<'a>,
        },
        CheckPrefillStatusResponse {
            payload: &'a [u8],
            value: bool,
        },
        KvCacheSendResponse {
            payload: &'a [u8],
            value: bool,
        },
        KvCacheReceiveResponse {
            payload: &'a [u8],
            fb: schema::KvCacheReceiveResponsePayload<'a>,
        },
        KvCacheReleaseResponse {
            payload: &'a [u8],
            value: bool,
        },
        CheckKvCacheReleaseResponse {
            payload: &'a [u8],
            value: bool,
        },
        KvCacheSwapResponse {
            payload: &'a [u8],
            value: bool,
        },
        Error {
            payload: &'a [u8],
            message: String,
        },
    }

    impl<'a> BorrowedTypedMyelonResponse<'a> {
        pub fn kind(&self) -> MsgKind {
            match self {
                Self::RunResponse { .. } => MsgKind::RunResponse,
                Self::TransferPrefillResponse { .. } => MsgKind::TransferPrefillResponse,
                Self::ReceivePrefillResponse { .. } => MsgKind::ReceivePrefillResponse,
                Self::CheckPrefillStatusResponse { .. } => MsgKind::CheckPrefillStatusResponse,
                Self::KvCacheSendResponse { .. } => MsgKind::KvCacheSendResponse,
                Self::KvCacheReceiveResponse { .. } => MsgKind::KvCacheReceiveResponse,
                Self::KvCacheReleaseResponse { .. } => MsgKind::KvCacheReleaseResponse,
                Self::CheckKvCacheReleaseResponse { .. } => {
                    MsgKind::CheckKvCacheReleaseResponse
                }
                Self::KvCacheSwapResponse { .. } => MsgKind::KvCacheSwapResponse,
                Self::Error { .. } => MsgKind::Error,
            }
        }

        pub fn to_owned(&self) -> Result<MyelonResponse, CodecError> {
            let payload = match self {
                Self::RunResponse { payload, .. }
                | Self::TransferPrefillResponse { payload, .. }
                | Self::ReceivePrefillResponse { payload, .. }
                | Self::CheckPrefillStatusResponse { payload, .. }
                | Self::KvCacheSendResponse { payload, .. }
                | Self::KvCacheReceiveResponse { payload, .. }
                | Self::KvCacheReleaseResponse { payload, .. }
                | Self::CheckKvCacheReleaseResponse { payload, .. }
                | Self::KvCacheSwapResponse { payload, .. }
                | Self::Error { payload, .. } => *payload,
            };
            MyelonResponse::decode(self.kind().as_u8(), payload).map_err(CodecError::decode)
        }

        fn from_payload(tag: u8, payload: &'a [u8]) -> Result<Self, CodecError> {
            match MsgKind::from_u8(tag).map_err(CodecError::decode)? {
                MsgKind::RunResponse => Ok(Self::RunResponse {
                    payload,
                    fb: flatbuffers::root::<schema::RunResponsePayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::TransferPrefillResponse => {
                    let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::TransferPrefillResponse {
                        payload,
                        value: fb.value(),
                    })
                }
                MsgKind::ReceivePrefillResponse => Ok(Self::ReceivePrefillResponse {
                    payload,
                    fb: flatbuffers::root::<schema::ReceivePrefillResponsePayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::CheckPrefillStatusResponse => {
                    let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::CheckPrefillStatusResponse {
                        payload,
                        value: fb.value(),
                    })
                }
                MsgKind::KvCacheSendResponse => {
                    let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::KvCacheSendResponse {
                        payload,
                        value: fb.value(),
                    })
                }
                MsgKind::KvCacheReceiveResponse => Ok(Self::KvCacheReceiveResponse {
                    payload,
                    fb: flatbuffers::root::<schema::KvCacheReceiveResponsePayload>(payload)
                        .map_err(CodecError::decode)?,
                }),
                MsgKind::KvCacheReleaseResponse => {
                    let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::KvCacheReleaseResponse {
                        payload,
                        value: fb.value(),
                    })
                }
                MsgKind::CheckKvCacheReleaseResponse => {
                    let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::CheckKvCacheReleaseResponse {
                        payload,
                        value: fb.value(),
                    })
                }
                MsgKind::KvCacheSwapResponse => {
                    let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                        .map_err(CodecError::decode)?;
                    Ok(Self::KvCacheSwapResponse {
                        payload,
                        value: fb.value(),
                    })
                }
                MsgKind::Error => Ok(Self::Error {
                    payload,
                    message: String::from_utf8_lossy(payload).into_owned(),
                }),
                other => Err(CodecError::decode(format!(
                    "request kind {:?} is not a typed response payload",
                    other
                ))),
            }
        }
    }

    impl ZeroCopyCodec for TypedMyelonRequest {
        type Archived<'a> = BorrowedTypedMyelonRequest<'a>;

        fn access<'a>(bytes: &'a [u8]) -> Result<Self::Archived<'a>, CodecError> {
            let (tag, payload) = decode_envelope(bytes)?;
            BorrowedTypedMyelonRequest::from_payload(tag, payload)
        }
    }

    impl ZeroCopyCodec for TypedMyelonResponse {
        type Archived<'a> = BorrowedTypedMyelonResponse<'a>;

        fn access<'a>(bytes: &'a [u8]) -> Result<Self::Archived<'a>, CodecError> {
            let (tag, payload) = decode_envelope(bytes)?;
            BorrowedTypedMyelonResponse::from_payload(tag, payload)
        }
    }
}

#[cfg(all(not(feature = "codec-rkyv"), feature = "codec-flatbuf"))]
pub use typed_flatbuf::{BorrowedTypedMyelonRequest, BorrowedTypedMyelonResponse};

impl Codec for TypedMyelonRequest {
    type Encoded = Vec<u8>;

    fn encode(&self) -> Result<Self::Encoded, CodecError> {
        let payload = self.0.encode().map_err(CodecError::encode)?;
        Ok(encode_envelope(self.0.kind().as_u8(), &payload))
    }

    fn decode(bytes: &[u8]) -> Result<Self, CodecError> {
        let (tag, payload) = decode_envelope(bytes)?;
        let request = MyelonRequest::decode(tag, payload).map_err(CodecError::decode)?;
        Ok(Self(request))
    }
}

impl Codec for TypedMyelonResponse {
    type Encoded = Vec<u8>;

    fn encode(&self) -> Result<Self::Encoded, CodecError> {
        let payload = self.0.encode().map_err(CodecError::encode)?;
        Ok(encode_envelope(self.0.kind().as_u8(), &payload))
    }

    fn decode(bytes: &[u8]) -> Result<Self, CodecError> {
        let (tag, payload) = decode_envelope(bytes)?;
        let response = MyelonResponse::decode(tag, payload).map_err(CodecError::decode)?;
        Ok(Self(response))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::utils::config::SamplingParams;

    #[test]
    fn typed_request_round_trip_preserves_prefill_payload() {
        let request = TypedMyelonRequest(MyelonRequest::RunPrefill {
            sequences: vec![crate::core::sequence::Sequence::new(
                vec![1, 2, 3, 4],
                16,
                SamplingParams::default(),
                &None,
                0,
            )],
        });

        let bytes = request.encode().unwrap();
        let decoded = TypedMyelonRequest::decode(&bytes).unwrap().into_inner();

        match decoded {
            MyelonRequest::RunPrefill { sequences } => {
                assert_eq!(sequences.len(), 1);
                assert_eq!(sequences[0].token_ids, vec![1, 2, 3, 4]);
            }
            other => panic!("unexpected decoded request: {other:?}"),
        }
    }

    #[test]
    fn typed_response_round_trip_preserves_run_outputs() {
        let response = TypedMyelonResponse(MyelonResponse::RunResponse(vec![7, 8, 9]));

        let bytes = response.encode().unwrap();
        let decoded = TypedMyelonResponse::decode(&bytes).unwrap().into_inner();

        match decoded {
            MyelonResponse::RunResponse(output_ids) => assert_eq!(output_ids, vec![7, 8, 9]),
            other => panic!("unexpected decoded response: {other:?}"),
        }
    }

    #[test]
    fn typed_envelope_rejects_short_payloads() {
        let error = TypedMyelonRequest::decode(&[1, 2, 3])
            .unwrap_err()
            .to_string();
        assert!(error.contains("typed Myelon envelope too short"));
    }

    #[cfg(feature = "codec-rkyv")]
    #[test]
    fn typed_request_zero_copy_access_preserves_kind() {
        let request = TypedMyelonRequest(MyelonRequest::FinishDecode { sequence_id: 17 });
        let bytes = request.encode().unwrap();
        let archived = TypedMyelonRequest::access(&bytes).unwrap();
        match archived {
            BorrowedTypedMyelonRequest::FinishDecode { sequence_id, .. } => {
                assert_eq!(sequence_id, 17);
            }
            _ => panic!("unexpected archived request kind"),
        }
    }

    #[cfg(feature = "codec-flatbuf")]
    #[test]
    fn typed_response_zero_copy_access_preserves_kind() {
        let response = TypedMyelonResponse(MyelonResponse::KvCacheSendResponse(true));
        let bytes = response.encode().unwrap();
        let archived = TypedMyelonResponse::access(&bytes).unwrap();
        match archived {
            BorrowedTypedMyelonResponse::KvCacheSendResponse { value, .. } => {
                assert!(value);
            }
            _ => panic!("unexpected archived response kind"),
        }
    }
}
