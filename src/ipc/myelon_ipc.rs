use anyhow::{Context, Result};
use candle_core::Result as CandleResult;
use interprocess::local_socket::Stream as LocalStream;
use interprocess::TryClone;
use myelon_playground::transport::{
    AlignedFixedFrame, FixedFrame, FramedTransportConsumer, FramedTransportProducer,
    MmapFramedTransportConsumer, MmapFramedTransportProducer, ReassemblyBuffer,
};
pub use myelon_playground::{MyelonTransportLayout, MyelonWaitStrategy};
use std::collections::HashMap;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};

use myelon_playground::{
    MmapTransportLayout, MmapTypedConsumer, MmapTypedProducer, TypedConsumer, TypedProducer,
};
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::time::Instant;

use crate::core::sequence::{DecodeSequence, Sequence};
use crate::ipc::typed_codec::{
    BorrowedTypedMyelonRequest, BorrowedTypedMyelonResponse, TypedMyelonRequest,
    TypedMyelonResponse,
};
use crate::log_info;
use crate::runner::{receive_local, send_local, MessageType};

pub const RPC_FRAME_HEADER_BYTES: usize = 12;
pub const RESPONSE_FRAME_HEADER_BYTES: usize = 12;
pub const RPC_FRAME_DATA_BYTES: usize = 64 * 1024 - RPC_FRAME_HEADER_BYTES;
pub const RESPONSE_FRAME_DATA_BYTES: usize = 4 * 1024 - RESPONSE_FRAME_HEADER_BYTES;
pub const VLLM_RS_DEFAULT_MYELON_RPC_DEPTH: usize = 8192;
pub const VLLM_RS_DEFAULT_MYELON_RESPONSE_DEPTH: usize = 8192;

/// Bytes of monotonic request_id prepended to framed Myelon payloads (LE u64).
/// Engine assigns the id; runner echoes it in the response. The engine validates
/// the echoed id matches the expected id before parsing the response value, which
/// catches per-rank response-ring drift (the PD tp2/tp2 bug).
pub const REQUEST_ID_BYTES: usize = 8;
static MYELON_INSTRUMENT: Lazy<bool> = Lazy::new(|| {
    std::env::var("MYELON_INSTRUMENT")
        .map(|v| v == "1")
        .unwrap_or(false)
});

#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct PublishStats {
    payload_bytes: usize,
    encode_ns: u128,
    publish_ns: u128,
}

#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct ResponseRecvStats {
    request_id: u64,
    payload_bytes: usize,
    collect_ns: u128,
    decode_ns: u128,
}

fn msg_kind_name(kind: MsgKind) -> &'static str {
    match kind {
        MsgKind::RunPrefill => "RunPrefill",
        MsgKind::RunDecode => "RunDecode",
        MsgKind::FinishDecode => "FinishDecode",
        MsgKind::Cancel => "Cancel",
        MsgKind::Shutdown => "Shutdown",
        MsgKind::TransferPrefill => "TransferPrefill",
        MsgKind::ReceivePrefill => "ReceivePrefill",
        MsgKind::CheckPrefillStatus => "CheckPrefillStatus",
        MsgKind::KvCacheSend => "KvCacheSend",
        MsgKind::KvCacheReceive => "KvCacheReceive",
        MsgKind::KvCacheRelease => "KvCacheRelease",
        MsgKind::CheckKvCacheRelease => "CheckKvCacheRelease",
        MsgKind::KvCacheSwap => "KvCacheSwap",
        MsgKind::RunResponse => "RunResponse",
        MsgKind::Error => "Error",
        MsgKind::TransferPrefillResponse => "TransferPrefillResponse",
        MsgKind::ReceivePrefillResponse => "ReceivePrefillResponse",
        MsgKind::CheckPrefillStatusResponse => "CheckPrefillStatusResponse",
        MsgKind::KvCacheSendResponse => "KvCacheSendResponse",
        MsgKind::KvCacheReceiveResponse => "KvCacheReceiveResponse",
        MsgKind::KvCacheReleaseResponse => "KvCacheReleaseResponse",
        MsgKind::CheckKvCacheReleaseResponse => "CheckKvCacheReleaseResponse",
        MsgKind::KvCacheSwapResponse => "KvCacheSwapResponse",
        MsgKind::TypedRequest => "TypedRequest",
        MsgKind::TypedResponse => "TypedResponse",
    }
}

fn access_mode_name(mode: MyelonTransportAccessMode) -> &'static str {
    match mode {
        MyelonTransportAccessMode::Owned => "owned",
        MyelonTransportAccessMode::Typed => "typed",
    }
}

fn emit_ipc_instr(
    request_id: u64,
    request_kind: MsgKind,
    access_mode: MyelonTransportAccessMode,
    payload_bytes: usize,
    response_payload_bytes: usize,
    response_count: usize,
    encode_ns: u128,
    publish_ns: u128,
    collect_ns: u128,
    decode_ns: u128,
    status: &str,
) {
    if !*MYELON_INSTRUMENT {
        return;
    }
    println!(
        "[MyelonInstr] {}",
        json!({
            "scope": "ipc",
            "request_id": request_id,
            "request_kind": msg_kind_name(request_kind),
            "request_kind_id": request_kind.as_u8(),
            "access_mode": access_mode_name(access_mode),
            "payload_bytes": payload_bytes,
            "response_payload_bytes": response_payload_bytes,
            "response_count": response_count,
            "encode_ns": encode_ns,
            "publish_ns": publish_ns,
            "collect_ns": collect_ns,
            "decode_ns": decode_ns,
            "status": status,
        })
    );
}

/// Prepend `request_id` (LE u64) to `payload`. Used by framed transport publish path.
fn prepend_request_id(request_id: u64, payload: &[u8]) -> Vec<u8> {
    let mut buf = Vec::with_capacity(REQUEST_ID_BYTES + payload.len());
    buf.extend_from_slice(&request_id.to_le_bytes());
    buf.extend_from_slice(payload);
    buf
}

/// Split a framed payload that starts with a `REQUEST_ID_BYTES` prefix.
fn split_request_id(bytes: &[u8]) -> CandleResult<(u64, &[u8])> {
    if bytes.len() < REQUEST_ID_BYTES {
        candle_core::bail!(
            "Myelon framed payload too short for request_id prefix: {} bytes",
            bytes.len()
        );
    }
    let id = u64::from_le_bytes(
        bytes[..REQUEST_ID_BYTES]
            .try_into()
            .expect("slice length checked"),
    );
    Ok((id, &bytes[REQUEST_ID_BYTES..]))
}

pub type RpcFrame = FixedFrame<RPC_FRAME_DATA_BYTES>;
pub type ResponseFrame = FixedFrame<RESPONSE_FRAME_DATA_BYTES>;
pub type TypedRpcFrame = AlignedFixedFrame<RPC_FRAME_DATA_BYTES>;
pub type TypedResponseFrame = AlignedFixedFrame<RESPONSE_FRAME_DATA_BYTES>;

#[derive(Copy, Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MyelonTransportBackend {
    Shm,
    Mmap,
}

impl MyelonTransportBackend {
    pub fn parse(value: Option<&str>) -> CandleResult<Self> {
        match value.unwrap_or("shm") {
            "shm" => Ok(Self::Shm),
            "mmap" => Ok(Self::Mmap),
            other => candle_core::bail!("unsupported myelon_backend '{other}'"),
        }
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MyelonTransportAccessMode {
    Owned,
    Typed,
}

impl MyelonTransportAccessMode {
    pub fn parse(value: Option<&str>) -> CandleResult<Self> {
        match value.unwrap_or("owned") {
            "owned" => Ok(Self::Owned),
            "typed" => Ok(Self::Typed),
            other => candle_core::bail!("unsupported myelon_access_mode '{other}'"),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct MyelonTransportConfig {
    pub rpc_depth: usize,
    pub response_depth: usize,
    pub wait_strategy: MyelonWaitStrategy,
    pub backend: MyelonTransportBackend,
    pub access_mode: MyelonTransportAccessMode,
}

impl MyelonTransportConfig {
    pub fn new(
        rpc_depth: usize,
        response_depth: usize,
        wait_strategy: MyelonWaitStrategy,
        backend: MyelonTransportBackend,
        access_mode: MyelonTransportAccessMode,
    ) -> CandleResult<Self> {
        if rpc_depth == 0 {
            candle_core::bail!("myelon_rpc_depth must be greater than zero");
        }
        if response_depth == 0 {
            candle_core::bail!("myelon_response_depth must be greater than zero");
        }
        Ok(Self {
            rpc_depth,
            response_depth,
            wait_strategy,
            backend,
            access_mode,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunnerMyelonTransportConfig {
    pub rank: usize,
    pub rpc_ring_name: String,
    pub rpc_depth: usize,
    pub response_ring_name: String,
    pub response_depth: usize,
    pub wait_strategy: MyelonWaitStrategy,
    pub backend: MyelonTransportBackend,
    pub access_mode: MyelonTransportAccessMode,
    pub mmap_root_dir: Option<String>,
}

impl RunnerMyelonTransportConfig {
    pub fn for_rank(
        layout: &MyelonTransportLayout,
        rank: usize,
        transport_config: &MyelonTransportConfig,
        mmap_root_dir: Option<&Path>,
    ) -> CandleResult<Self> {
        Ok(Self {
            rank,
            rpc_ring_name: layout.rpc_ring_name().to_string(),
            rpc_depth: layout.rpc_depth(),
            response_ring_name: layout
                .response_ring_name(rank)
                .map_err(myelon_to_candle)?
                .to_string(),
            response_depth: layout.response_depth(),
            wait_strategy: transport_config.wait_strategy,
            backend: transport_config.backend,
            access_mode: transport_config.access_mode,
            mmap_root_dir: mmap_root_dir.map(|path| path.display().to_string()),
        })
    }

    pub fn mmap_root_dir(&self) -> CandleResult<&Path> {
        self.mmap_root_dir
            .as_deref()
            .map(Path::new)
            .ok_or_else(|| candle_core::Error::Msg("missing mmap root dir".to_string()))
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum MsgKind {
    RunPrefill = 1,
    RunDecode = 2,
    FinishDecode = 3,
    Cancel = 4,
    Shutdown = 5,
    TransferPrefill = 6,
    ReceivePrefill = 7,
    CheckPrefillStatus = 8,
    KvCacheSend = 9,
    KvCacheReceive = 10,
    KvCacheRelease = 11,
    CheckKvCacheRelease = 12,
    KvCacheSwap = 13,
    RunResponse = 100,
    Error = 101,
    TransferPrefillResponse = 102,
    ReceivePrefillResponse = 103,
    CheckPrefillStatusResponse = 104,
    KvCacheSendResponse = 105,
    KvCacheReceiveResponse = 106,
    KvCacheReleaseResponse = 107,
    CheckKvCacheReleaseResponse = 108,
    KvCacheSwapResponse = 109,
    TypedRequest = 200,
    TypedResponse = 201,
}

impl MsgKind {
    pub const fn as_u8(self) -> u8 {
        self as u8
    }

    pub fn from_u8(kind: u8) -> CandleResult<Self> {
        match kind {
            x if x == Self::RunPrefill as u8 => Ok(Self::RunPrefill),
            x if x == Self::RunDecode as u8 => Ok(Self::RunDecode),
            x if x == Self::FinishDecode as u8 => Ok(Self::FinishDecode),
            x if x == Self::Cancel as u8 => Ok(Self::Cancel),
            x if x == Self::Shutdown as u8 => Ok(Self::Shutdown),
            x if x == Self::TransferPrefill as u8 => Ok(Self::TransferPrefill),
            x if x == Self::ReceivePrefill as u8 => Ok(Self::ReceivePrefill),
            x if x == Self::CheckPrefillStatus as u8 => Ok(Self::CheckPrefillStatus),
            x if x == Self::KvCacheSend as u8 => Ok(Self::KvCacheSend),
            x if x == Self::KvCacheReceive as u8 => Ok(Self::KvCacheReceive),
            x if x == Self::KvCacheRelease as u8 => Ok(Self::KvCacheRelease),
            x if x == Self::CheckKvCacheRelease as u8 => Ok(Self::CheckKvCacheRelease),
            x if x == Self::KvCacheSwap as u8 => Ok(Self::KvCacheSwap),
            x if x == Self::RunResponse as u8 => Ok(Self::RunResponse),
            x if x == Self::Error as u8 => Ok(Self::Error),
            x if x == Self::TransferPrefillResponse as u8 => Ok(Self::TransferPrefillResponse),
            x if x == Self::ReceivePrefillResponse as u8 => Ok(Self::ReceivePrefillResponse),
            x if x == Self::CheckPrefillStatusResponse as u8 => {
                Ok(Self::CheckPrefillStatusResponse)
            }
            x if x == Self::KvCacheSendResponse as u8 => Ok(Self::KvCacheSendResponse),
            x if x == Self::KvCacheReceiveResponse as u8 => Ok(Self::KvCacheReceiveResponse),
            x if x == Self::KvCacheReleaseResponse as u8 => Ok(Self::KvCacheReleaseResponse),
            x if x == Self::CheckKvCacheReleaseResponse as u8 => {
                Ok(Self::CheckKvCacheReleaseResponse)
            }
            x if x == Self::KvCacheSwapResponse as u8 => Ok(Self::KvCacheSwapResponse),
            x if x == Self::TypedRequest as u8 => Ok(Self::TypedRequest),
            x if x == Self::TypedResponse as u8 => Ok(Self::TypedResponse),
            _ => candle_core::bail!("unexpected Myelon message kind {}", kind),
        }
    }
}

fn myelon_to_candle<E: std::fmt::Display>(error: E) -> candle_core::Error {
    candle_core::Error::Msg(error.to_string())
}

#[cfg(not(any(feature = "codec-rkyv", feature = "codec-flatbuf")))]
fn encode_u32_slice(values: &[u32]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(4 + values.len() * std::mem::size_of::<u32>());
    bytes.extend_from_slice(&(values.len() as u32).to_le_bytes());
    for value in values {
        bytes.extend_from_slice(&value.to_le_bytes());
    }
    bytes
}

#[cfg(not(any(feature = "codec-rkyv", feature = "codec-flatbuf")))]
fn decode_u32_slice(payload: &[u8]) -> CandleResult<Vec<u32>> {
    if payload.len() < 4 {
        candle_core::bail!(
            "Myelon RunResponse payload too short: {} bytes",
            payload.len()
        );
    }
    let count = u32::from_le_bytes(payload[..4].try_into().expect("slice length checked")) as usize;
    let expected_len = 4 + count * std::mem::size_of::<u32>();
    if payload.len() != expected_len {
        candle_core::bail!(
            "Myelon RunResponse payload len {} did not match expected {} for {} ids",
            payload.len(),
            expected_len,
            count
        );
    }
    let mut values = Vec::with_capacity(count);
    for chunk in payload[4..].chunks_exact(std::mem::size_of::<u32>()) {
        values.push(u32::from_le_bytes(
            chunk.try_into().expect("chunk size is exactly four bytes"),
        ));
    }
    Ok(values)
}

pub fn resolve_myelon_transport_config(
    rpc_depth: Option<usize>,
    response_depth: Option<usize>,
    busy_spin: Option<bool>,
    backend: Option<&str>,
    access_mode: Option<&str>,
) -> CandleResult<MyelonTransportConfig> {
    let wait_strategy = if busy_spin.unwrap_or(true) {
        MyelonWaitStrategy::BusySpin
    } else {
        MyelonWaitStrategy::Block
    };
    MyelonTransportConfig::new(
        rpc_depth.unwrap_or(VLLM_RS_DEFAULT_MYELON_RPC_DEPTH),
        response_depth.unwrap_or(VLLM_RS_DEFAULT_MYELON_RESPONSE_DEPTH),
        wait_strategy,
        MyelonTransportBackend::parse(backend)?,
        MyelonTransportAccessMode::parse(access_mode)?,
    )
}

pub enum RpcBroadcastProducer {
    ShmFramed {
        inner: FramedTransportProducer<RpcFrame>,
    },
    MmapFramed {
        inner: MmapFramedTransportProducer<RpcFrame>,
    },
    ShmTyped {
        inner: TypedProducer<TypedRpcFrame>,
    },
    MmapTyped {
        inner: MmapTypedProducer<TypedRpcFrame>,
    },
}

impl RpcBroadcastProducer {
    pub fn create_shm(name: &str, depth: usize) -> Result<Self> {
        let inner = FramedTransportProducer::<RpcFrame>::create(name, depth)
            .with_context(|| format!("failed to create rpc ring '{name}'"))?;
        Ok(Self::ShmFramed { inner })
    }

    pub fn create_typed_shm(name: &str, depth: usize) -> Result<Self> {
        let inner = TypedProducer::<TypedRpcFrame>::create(name, depth)
            .with_context(|| format!("failed to create typed rpc ring '{name}'"))?;
        Ok(Self::ShmTyped { inner })
    }

    pub fn create_mmap(layout: MmapTransportLayout, depth: usize) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapFramedTransportProducer::<RpcFrame>::create(layout, depth)
            .with_context(|| format!("failed to create mmap rpc ring '{segment}'"))?;
        Ok(Self::MmapFramed { inner })
    }

    pub fn create_typed_mmap(layout: MmapTransportLayout, depth: usize) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapTypedProducer::<TypedRpcFrame>::create(layout, depth)
            .with_context(|| format!("failed to create typed mmap rpc ring '{segment}'"))?;
        Ok(Self::MmapTyped { inner })
    }

    pub fn publish_raw(&mut self, payload: &[u8], kind: MsgKind) {
        match self {
            Self::ShmFramed { inner } => inner.publish(payload, kind.as_u8()),
            Self::MmapFramed { inner } => inner.publish(payload, kind.as_u8()),
            Self::ShmTyped { .. } | Self::MmapTyped { .. } => {
                panic!("typed rpc producer cannot publish raw framed payloads");
            }
        }
    }

    pub(crate) fn publish_request(
        &mut self,
        request: &MyelonRequest,
        request_id: u64,
    ) -> CandleResult<PublishStats> {
        match self {
            Self::ShmFramed { inner } => {
                let t_encode = Instant::now();
                let bytes = request.encode()?;
                let stamped = prepend_request_id(request_id, &bytes);
                let encode_ns = t_encode.elapsed().as_nanos();
                let t_publish = Instant::now();
                inner.publish(&stamped, request.kind().as_u8());
                Ok(PublishStats {
                    payload_bytes: stamped.len(),
                    encode_ns,
                    publish_ns: t_publish.elapsed().as_nanos(),
                })
            }
            Self::MmapFramed { inner } => {
                let t_encode = Instant::now();
                let bytes = request.encode()?;
                let stamped = prepend_request_id(request_id, &bytes);
                let encode_ns = t_encode.elapsed().as_nanos();
                let t_publish = Instant::now();
                inner.publish(&stamped, request.kind().as_u8());
                Ok(PublishStats {
                    payload_bytes: stamped.len(),
                    encode_ns,
                    publish_ns: t_publish.elapsed().as_nanos(),
                })
            }
            Self::ShmTyped { inner } => {
                let typed = TypedMyelonRequest::new(request_id, request.clone());
                let t_publish = Instant::now();
                inner
                    .publish(&typed, MsgKind::TypedRequest.as_u8())
                    .map_err(myelon_to_candle)?;
                Ok(PublishStats {
                    payload_bytes: 0,
                    encode_ns: 0,
                    publish_ns: t_publish.elapsed().as_nanos(),
                })
            }
            Self::MmapTyped { inner } => {
                let typed = TypedMyelonRequest::new(request_id, request.clone());
                let t_publish = Instant::now();
                inner
                    .publish(&typed, MsgKind::TypedRequest.as_u8())
                    .map_err(myelon_to_candle)?;
                Ok(PublishStats {
                    payload_bytes: 0,
                    encode_ns: 0,
                    publish_ns: t_publish.elapsed().as_nanos(),
                })
            }
        }
    }
}

pub enum RpcBroadcastConsumer {
    ShmFramed {
        inner: FramedTransportConsumer<RpcFrame>,
        reassembly: ReassemblyBuffer,
    },
    MmapFramed {
        inner: MmapFramedTransportConsumer<RpcFrame>,
        reassembly: ReassemblyBuffer,
    },
    ShmTyped {
        inner: TypedConsumer<TypedRpcFrame>,
        reassembly: ReassemblyBuffer,
    },
    MmapTyped {
        inner: MmapTypedConsumer<TypedRpcFrame>,
        reassembly: ReassemblyBuffer,
    },
}

impl RpcBroadcastConsumer {
    pub fn attach_shm(name: &str, depth: usize, wait_strategy: MyelonWaitStrategy) -> Result<Self> {
        let inner = FramedTransportConsumer::<RpcFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach rpc ring '{name}'"))?;
        Ok(Self::ShmFramed {
            inner,
            reassembly: ReassemblyBuffer::new(RPC_FRAME_DATA_BYTES),
        })
    }

    pub fn attach_typed_shm(
        name: &str,
        depth: usize,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        let inner = TypedConsumer::<TypedRpcFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach typed rpc ring '{name}'"))?;
        Ok(Self::ShmTyped {
            inner,
            reassembly: ReassemblyBuffer::new(RPC_FRAME_DATA_BYTES),
        })
    }

    pub fn attach_mmap(
        layout: MmapTransportLayout,
        depth: usize,
        consumer_id: &str,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapFramedTransportConsumer::<RpcFrame>::attach(
            layout,
            depth,
            consumer_id,
            wait_strategy,
        )
        .with_context(|| format!("failed to attach mmap rpc ring '{segment}'"))?;
        Ok(Self::MmapFramed {
            inner,
            reassembly: ReassemblyBuffer::new(RPC_FRAME_DATA_BYTES),
        })
    }

    pub fn attach_typed_mmap(
        layout: MmapTransportLayout,
        depth: usize,
        consumer_id: &str,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner =
            MmapTypedConsumer::<TypedRpcFrame>::attach(layout, depth, consumer_id, wait_strategy)
                .with_context(|| format!("failed to attach typed mmap rpc ring '{segment}'"))?;
        Ok(Self::MmapTyped {
            inner,
            reassembly: ReassemblyBuffer::new(RPC_FRAME_DATA_BYTES),
        })
    }

    pub fn has_coordination_support(&self) -> bool {
        match self {
            Self::ShmFramed { inner, .. } => inner.has_coordination_support(),
            Self::MmapFramed { inner, .. } => inner.has_coordination_support(),
            Self::ShmTyped { .. } | Self::MmapTyped { .. } => true,
        }
    }

    pub fn recv_request_blocking_owned(&mut self) -> CandleResult<(u64, MyelonRequest)> {
        match self {
            Self::ShmFramed { inner, .. } => {
                let (kind, payload) = inner.recv_message_blocking_owned();
                let (request_id, body) = split_request_id(&payload)?;
                let request = MyelonRequest::decode(kind, body)?;
                Ok((request_id, request))
            }
            Self::MmapFramed { inner, .. } => {
                let (kind, payload) = inner.recv_message_blocking_owned();
                let (request_id, body) = split_request_id(&payload)?;
                let request = MyelonRequest::decode(kind, body)?;
                Ok((request_id, request))
            }
            Self::ShmTyped { inner, .. } => {
                let (kind, typed) = inner
                    .recv_owned::<TypedMyelonRequest>()
                    .map_err(myelon_to_candle)?;
                if kind != MsgKind::TypedRequest.as_u8() {
                    candle_core::bail!("unexpected typed request transport kind {}", kind);
                }
                let (id, request) = typed.into_parts();
                Ok((id, request))
            }
            Self::MmapTyped { inner, .. } => {
                let (kind, typed) = inner
                    .recv_owned::<TypedMyelonRequest>()
                    .map_err(myelon_to_candle)?;
                if kind != MsgKind::TypedRequest.as_u8() {
                    candle_core::bail!("unexpected typed request transport kind {}", kind);
                }
                let (id, request) = typed.into_parts();
                Ok((id, request))
            }
        }
    }

    pub fn with_request_blocking_typed<R>(
        &mut self,
        mut handler: impl for<'a> FnMut(u64, BorrowedTypedMyelonRequest<'a>) -> CandleResult<R>,
    ) -> CandleResult<R> {
        match self {
            Self::ShmTyped { inner, reassembly } => inner
                .recv_leased::<TypedMyelonRequest, _, _>(reassembly, |kind, archived| {
                    if kind != MsgKind::TypedRequest.as_u8() {
                        candle_core::bail!("unexpected typed request transport kind {}", kind);
                    }
                    let (id, request) = archived;
                    handler(id, request)
                })
                .map_err(myelon_to_candle)?,
            Self::MmapTyped { inner, reassembly } => inner
                .recv_leased::<TypedMyelonRequest, _, _>(reassembly, |kind, archived| {
                    if kind != MsgKind::TypedRequest.as_u8() {
                        candle_core::bail!("unexpected typed request transport kind {}", kind);
                    }
                    let (id, request) = archived;
                    handler(id, request)
                })
                .map_err(myelon_to_candle)?,
            Self::ShmFramed { .. } | Self::MmapFramed { .. } => {
                candle_core::bail!("framed request transport does not support typed leased access")
            }
        }
    }

}

pub enum ResponseProducer {
    ShmFramed {
        inner: FramedTransportProducer<ResponseFrame>,
    },
    MmapFramed {
        inner: MmapFramedTransportProducer<ResponseFrame>,
    },
    ShmTyped {
        inner: TypedProducer<TypedResponseFrame>,
    },
    MmapTyped {
        inner: MmapTypedProducer<TypedResponseFrame>,
    },
}

impl ResponseProducer {
    pub fn create_shm(name: &str, depth: usize) -> Result<Self> {
        let inner = FramedTransportProducer::<ResponseFrame>::create(name, depth)
            .with_context(|| format!("failed to create response ring '{name}'"))?;
        Ok(Self::ShmFramed { inner })
    }

    pub fn create_typed_shm(name: &str, depth: usize) -> Result<Self> {
        let inner = TypedProducer::<TypedResponseFrame>::create(name, depth)
            .with_context(|| format!("failed to create typed response ring '{name}'"))?;
        Ok(Self::ShmTyped { inner })
    }

    pub fn create_mmap(layout: MmapTransportLayout, depth: usize) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapFramedTransportProducer::<ResponseFrame>::create(layout, depth)
            .with_context(|| format!("failed to create mmap response ring '{segment}'"))?;
        Ok(Self::MmapFramed { inner })
    }

    pub fn create_typed_mmap(layout: MmapTransportLayout, depth: usize) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapTypedProducer::<TypedResponseFrame>::create(layout, depth)
            .with_context(|| format!("failed to create typed mmap response ring '{segment}'"))?;
        Ok(Self::MmapTyped { inner })
    }

    pub fn send_raw(&mut self, payload: &[u8], kind: MsgKind) {
        match self {
            Self::ShmFramed { inner } => inner.publish(payload, kind.as_u8()),
            Self::MmapFramed { inner } => inner.publish(payload, kind.as_u8()),
            Self::ShmTyped { .. } | Self::MmapTyped { .. } => {
                panic!("typed response producer cannot publish raw framed payloads");
            }
        }
    }

    pub fn send_response(
        &mut self,
        response: &MyelonResponse,
        request_id: u64,
    ) -> CandleResult<()> {
        match self {
            Self::ShmFramed { inner } => {
                let bytes = response.encode()?;
                let stamped = prepend_request_id(request_id, &bytes);
                inner.publish(&stamped, response.kind().as_u8());
                Ok(())
            }
            Self::MmapFramed { inner } => {
                let bytes = response.encode()?;
                let stamped = prepend_request_id(request_id, &bytes);
                inner.publish(&stamped, response.kind().as_u8());
                Ok(())
            }
            Self::ShmTyped { inner } => inner
                .publish(
                    &TypedMyelonResponse::new(request_id, response.clone()),
                    MsgKind::TypedResponse.as_u8(),
                )
                .map_err(myelon_to_candle),
            Self::MmapTyped { inner } => inner
                .publish(
                    &TypedMyelonResponse::new(request_id, response.clone()),
                    MsgKind::TypedResponse.as_u8(),
                )
                .map_err(myelon_to_candle),
        }
    }

    pub fn send_error(&mut self, error: impl std::fmt::Display, request_id: u64) {
        let response = MyelonResponse::Error(error.to_string());
        self.send_response(&response, request_id)
            .expect("MyelonResponse::Error should always serialize");
    }
}

pub enum ResponseConsumer {
    ShmFramed {
        inner: FramedTransportConsumer<ResponseFrame>,
        reassembly: ReassemblyBuffer,
    },
    MmapFramed {
        inner: MmapFramedTransportConsumer<ResponseFrame>,
        reassembly: ReassemblyBuffer,
    },
    ShmTyped {
        inner: TypedConsumer<TypedResponseFrame>,
        reassembly: ReassemblyBuffer,
    },
    MmapTyped {
        inner: MmapTypedConsumer<TypedResponseFrame>,
        reassembly: ReassemblyBuffer,
    },
}

impl ResponseConsumer {
    pub fn attach_shm(name: &str, depth: usize, wait_strategy: MyelonWaitStrategy) -> Result<Self> {
        let inner = FramedTransportConsumer::<ResponseFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach response ring '{name}'"))?;
        Ok(Self::ShmFramed {
            inner,
            reassembly: ReassemblyBuffer::new(RESPONSE_FRAME_DATA_BYTES),
        })
    }

    pub fn attach_typed_shm(
        name: &str,
        depth: usize,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        let inner = TypedConsumer::<TypedResponseFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach typed response ring '{name}'"))?;
        Ok(Self::ShmTyped {
            inner,
            reassembly: ReassemblyBuffer::new(RESPONSE_FRAME_DATA_BYTES),
        })
    }

    pub fn attach_mmap(
        layout: MmapTransportLayout,
        depth: usize,
        consumer_id: &str,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapFramedTransportConsumer::<ResponseFrame>::attach(
            layout,
            depth,
            consumer_id,
            wait_strategy,
        )
        .with_context(|| format!("failed to attach mmap response ring '{segment}'"))?;
        Ok(Self::MmapFramed {
            inner,
            reassembly: ReassemblyBuffer::new(RESPONSE_FRAME_DATA_BYTES),
        })
    }

    pub fn attach_typed_mmap(
        layout: MmapTransportLayout,
        depth: usize,
        consumer_id: &str,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapTypedConsumer::<TypedResponseFrame>::attach(
            layout,
            depth,
            consumer_id,
            wait_strategy,
        )
        .with_context(|| format!("failed to attach typed mmap response ring '{segment}'"))?;
        Ok(Self::MmapTyped {
            inner,
            reassembly: ReassemblyBuffer::new(RESPONSE_FRAME_DATA_BYTES),
        })
    }

    pub fn has_coordination_support(&self) -> bool {
        match self {
            Self::ShmFramed { inner, .. } => inner.has_coordination_support(),
            Self::MmapFramed { inner, .. } => inner.has_coordination_support(),
            Self::ShmTyped { .. } | Self::MmapTyped { .. } => true,
        }
    }

    pub(crate) fn recv_response_blocking_owned(
        &mut self,
    ) -> CandleResult<(ResponseRecvStats, MyelonResponse)> {
        match self {
            Self::ShmFramed { inner, .. } => {
                let t_collect = Instant::now();
                let (kind, payload) = inner.recv_message_blocking_owned();
                let collect_ns = t_collect.elapsed().as_nanos();
                let t_decode = Instant::now();
                let (id, body) = split_request_id(&payload)?;
                let response = MyelonResponse::decode(kind, body)?;
                Ok((
                    ResponseRecvStats {
                        request_id: id,
                        payload_bytes: payload.len(),
                        collect_ns,
                        decode_ns: t_decode.elapsed().as_nanos(),
                    },
                    response,
                ))
            }
            Self::MmapFramed { inner, .. } => {
                let t_collect = Instant::now();
                let (kind, payload) = inner.recv_message_blocking_owned();
                let collect_ns = t_collect.elapsed().as_nanos();
                let t_decode = Instant::now();
                let (id, body) = split_request_id(&payload)?;
                let response = MyelonResponse::decode(kind, body)?;
                Ok((
                    ResponseRecvStats {
                        request_id: id,
                        payload_bytes: payload.len(),
                        collect_ns,
                        decode_ns: t_decode.elapsed().as_nanos(),
                    },
                    response,
                ))
            }
            Self::ShmTyped { inner, .. } => {
                let t_collect = Instant::now();
                let (kind, typed) = inner
                    .recv_owned::<TypedMyelonResponse>()
                    .map_err(myelon_to_candle)?;
                let collect_ns = t_collect.elapsed().as_nanos();
                if kind != MsgKind::TypedResponse.as_u8() {
                    candle_core::bail!("unexpected typed response transport kind {}", kind);
                }
                let t_decode = Instant::now();
                let (id, response) = typed.into_parts();
                Ok((
                    ResponseRecvStats {
                        request_id: id,
                        payload_bytes: 0,
                        collect_ns,
                        decode_ns: t_decode.elapsed().as_nanos(),
                    },
                    response,
                ))
            }
            Self::MmapTyped { inner, .. } => {
                let t_collect = Instant::now();
                let (kind, typed) = inner
                    .recv_owned::<TypedMyelonResponse>()
                    .map_err(myelon_to_candle)?;
                let collect_ns = t_collect.elapsed().as_nanos();
                if kind != MsgKind::TypedResponse.as_u8() {
                    candle_core::bail!("unexpected typed response transport kind {}", kind);
                }
                let t_decode = Instant::now();
                let (id, response) = typed.into_parts();
                Ok((
                    ResponseRecvStats {
                        request_id: id,
                        payload_bytes: 0,
                        collect_ns,
                        decode_ns: t_decode.elapsed().as_nanos(),
                    },
                    response,
                ))
            }
        }
    }

    pub(crate) fn recv_response_blocking_typed(
        &mut self,
    ) -> CandleResult<(ResponseRecvStats, MyelonResponse)> {
        match self {
            Self::ShmTyped { inner, reassembly } => {
                let t_collect = Instant::now();
                let (request_id, response) = inner
                    .recv_leased::<TypedMyelonResponse, _, _>(reassembly, |kind, archived| {
                        if kind != MsgKind::TypedResponse.as_u8() {
                            candle_core::bail!("unexpected typed response transport kind {}", kind);
                        }
                        let (id, response) = archived;
                        let owned = response.to_owned().map_err(myelon_to_candle)?;
                        Ok((id, owned))
                    })
                    .map_err(myelon_to_candle)??;
                let collect_ns = t_collect.elapsed().as_nanos();
                Ok((
                    ResponseRecvStats {
                        request_id,
                        payload_bytes: 0,
                        collect_ns,
                        decode_ns: 0,
                    },
                    response,
                ))
            }
            Self::MmapTyped { inner, reassembly } => {
                let t_collect = Instant::now();
                let (request_id, response) = inner
                    .recv_leased::<TypedMyelonResponse, _, _>(reassembly, |kind, archived| {
                        if kind != MsgKind::TypedResponse.as_u8() {
                            candle_core::bail!("unexpected typed response transport kind {}", kind);
                        }
                        let (id, response) = archived;
                        let owned = response.to_owned().map_err(myelon_to_candle)?;
                        Ok((id, owned))
                    })
                    .map_err(myelon_to_candle)??;
                let collect_ns = t_collect.elapsed().as_nanos();
                Ok((
                    ResponseRecvStats {
                        request_id,
                        payload_bytes: 0,
                        collect_ns,
                        decode_ns: 0,
                    },
                    response,
                ))
            }
            Self::ShmFramed { .. } | Self::MmapFramed { .. } => {
                candle_core::bail!("framed response transport does not support typed leased access")
            }
        }
    }

    pub fn with_response_blocking_typed<R>(
        &mut self,
        mut handler: impl for<'a> FnMut(u64, BorrowedTypedMyelonResponse<'a>) -> CandleResult<R>,
    ) -> CandleResult<R> {
        match self {
            Self::ShmTyped { inner, reassembly } => inner
                .recv_leased::<TypedMyelonResponse, _, _>(reassembly, |kind, archived| {
                    if kind != MsgKind::TypedResponse.as_u8() {
                        candle_core::bail!("unexpected typed response transport kind {}", kind);
                    }
                    let (id, response) = archived;
                    handler(id, response)
                })
                .map_err(myelon_to_candle)?,
            Self::MmapTyped { inner, reassembly } => inner
                .recv_leased::<TypedMyelonResponse, _, _>(reassembly, |kind, archived| {
                    if kind != MsgKind::TypedResponse.as_u8() {
                        candle_core::bail!("unexpected typed response transport kind {}", kind);
                    }
                    let (id, response) = archived;
                    handler(id, response)
                })
                .map_err(myelon_to_candle)?,
            Self::ShmFramed { .. } | Self::MmapFramed { .. } => {
                candle_core::bail!("framed response transport does not support typed leased access")
            }
        }
    }

}

#[derive(Debug, Clone)]
pub enum MyelonRequest {
    RunPrefill {
        sequences: Vec<Sequence>,
    },
    RunDecode {
        sequences: Vec<DecodeSequence>,
    },
    FinishDecode {
        sequence_id: usize,
    },
    Cancel {
        sequence_id: usize,
    },
    TransferPrefill {
        sequence: Sequence,
    },
    ReceivePrefill {
        available_tokens: usize,
    },
    CheckPrefillStatus {
        sequence_id: usize,
    },
    KvCacheSend {
        sequence: Sequence,
        first_token: u32,
    },
    KvCacheReceive {
        sequence: Sequence,
    },
    KvCacheRelease {
        sequence_id: usize,
    },
    CheckKvCacheRelease {
        sequence_id: usize,
    },
    KvCacheSwap {
        mappings: HashMap<usize, usize>,
        swap_in: bool,
    },
    Shutdown,
}

impl MyelonRequest {
    pub const fn kind(&self) -> MsgKind {
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

    pub fn encode(&self) -> CandleResult<Vec<u8>> {
        #[cfg(feature = "codec-rkyv")]
        return crate::ipc::rkyv_codec::encode_request(self);

        #[cfg(feature = "codec-flatbuf")]
        return crate::ipc::flatbuf_codec::encode_request(self);

        #[cfg(not(any(feature = "codec-rkyv", feature = "codec-flatbuf")))]
        match self {
            Self::RunPrefill { sequences } => {
                bincode::serialize(&(sequences, true)).map_err(myelon_to_candle)
            }
            Self::RunDecode { sequences } => {
                bincode::serialize(&(sequences, false)).map_err(myelon_to_candle)
            }
            Self::FinishDecode { sequence_id } | Self::Cancel { sequence_id } => {
                bincode::serialize(sequence_id).map_err(myelon_to_candle)
            }
            Self::TransferPrefill { sequence } | Self::KvCacheReceive { sequence } => {
                bincode::serialize(sequence).map_err(myelon_to_candle)
            }
            Self::ReceivePrefill { available_tokens } => {
                bincode::serialize(available_tokens).map_err(myelon_to_candle)
            }
            Self::CheckPrefillStatus { sequence_id }
            | Self::KvCacheRelease { sequence_id }
            | Self::CheckKvCacheRelease { sequence_id } => {
                bincode::serialize(sequence_id).map_err(myelon_to_candle)
            }
            Self::KvCacheSend {
                sequence,
                first_token,
            } => bincode::serialize(&(sequence, first_token)).map_err(myelon_to_candle),
            Self::KvCacheSwap { mappings, swap_in } => {
                bincode::serialize(&(mappings, swap_in)).map_err(myelon_to_candle)
            }
            Self::Shutdown => Ok(Vec::new()),
        }
    }

    pub fn decode(kind: u8, payload: &[u8]) -> CandleResult<Self> {
        #[cfg(feature = "codec-rkyv")]
        return crate::ipc::rkyv_codec::decode_request(kind, payload);

        #[cfg(feature = "codec-flatbuf")]
        return crate::ipc::flatbuf_codec::decode_request(kind, payload);

        #[cfg(not(any(feature = "codec-rkyv", feature = "codec-flatbuf")))]
        match MsgKind::from_u8(kind)? {
            MsgKind::RunPrefill => {
                let (sequences, is_prefill): (Vec<Sequence>, bool) =
                    bincode::deserialize(payload).map_err(myelon_to_candle)?;
                if !is_prefill {
                    candle_core::bail!("RunPrefill request received with is_prefill=false");
                }
                Ok(Self::RunPrefill { sequences })
            }
            MsgKind::RunDecode => {
                let (sequences, is_prefill): (Vec<DecodeSequence>, bool) =
                    bincode::deserialize(payload).map_err(myelon_to_candle)?;
                if is_prefill {
                    candle_core::bail!("RunDecode request received with is_prefill=true");
                }
                Ok(Self::RunDecode { sequences })
            }
            MsgKind::FinishDecode => {
                let sequence_id = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::FinishDecode { sequence_id })
            }
            MsgKind::Cancel => {
                let sequence_id = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::Cancel { sequence_id })
            }
            MsgKind::TransferPrefill => {
                let sequence = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::TransferPrefill { sequence })
            }
            MsgKind::ReceivePrefill => {
                let available_tokens = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::ReceivePrefill { available_tokens })
            }
            MsgKind::CheckPrefillStatus => {
                let sequence_id = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::CheckPrefillStatus { sequence_id })
            }
            MsgKind::KvCacheSend => {
                let (sequence, first_token): (Sequence, u32) =
                    bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheSend {
                    sequence,
                    first_token,
                })
            }
            MsgKind::KvCacheReceive => {
                let sequence = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheReceive { sequence })
            }
            MsgKind::KvCacheRelease => {
                let sequence_id = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheRelease { sequence_id })
            }
            MsgKind::CheckKvCacheRelease => {
                let sequence_id = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::CheckKvCacheRelease { sequence_id })
            }
            MsgKind::KvCacheSwap => {
                let (mappings, swap_in): (HashMap<usize, usize>, bool) =
                    bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheSwap { mappings, swap_in })
            }
            MsgKind::Shutdown => {
                if !payload.is_empty() {
                    candle_core::bail!("Shutdown request must not carry a payload");
                }
                Ok(Self::Shutdown)
            }
            MsgKind::RunResponse
            | MsgKind::Error
            | MsgKind::TransferPrefillResponse
            | MsgKind::ReceivePrefillResponse
            | MsgKind::CheckPrefillStatusResponse
            | MsgKind::KvCacheSendResponse
            | MsgKind::KvCacheReceiveResponse
            | MsgKind::KvCacheReleaseResponse
            | MsgKind::CheckKvCacheReleaseResponse
            | MsgKind::KvCacheSwapResponse
            | MsgKind::TypedRequest
            | MsgKind::TypedResponse => {
                candle_core::bail!("response kind {} is not a request", kind);
            }
        }
    }
}

#[derive(Debug, Clone)]
pub enum MyelonResponse {
    RunResponse(Vec<u32>),
    TransferPrefillResponse(bool),
    ReceivePrefillResponse((bool, Option<Sequence>)),
    CheckPrefillStatusResponse(bool),
    KvCacheSendResponse(bool),
    KvCacheReceiveResponse((bool, u32, usize, usize)),
    KvCacheReleaseResponse(bool),
    CheckKvCacheReleaseResponse(bool),
    KvCacheSwapResponse(bool),
    Error(String),
}

impl MyelonResponse {
    pub const fn kind(&self) -> MsgKind {
        match self {
            Self::RunResponse(_) => MsgKind::RunResponse,
            Self::TransferPrefillResponse(_) => MsgKind::TransferPrefillResponse,
            Self::ReceivePrefillResponse(_) => MsgKind::ReceivePrefillResponse,
            Self::CheckPrefillStatusResponse(_) => MsgKind::CheckPrefillStatusResponse,
            Self::KvCacheSendResponse(_) => MsgKind::KvCacheSendResponse,
            Self::KvCacheReceiveResponse(_) => MsgKind::KvCacheReceiveResponse,
            Self::KvCacheReleaseResponse(_) => MsgKind::KvCacheReleaseResponse,
            Self::CheckKvCacheReleaseResponse(_) => MsgKind::CheckKvCacheReleaseResponse,
            Self::KvCacheSwapResponse(_) => MsgKind::KvCacheSwapResponse,
            Self::Error(_) => MsgKind::Error,
        }
    }

    pub fn encode(&self) -> CandleResult<Vec<u8>> {
        #[cfg(feature = "codec-rkyv")]
        return crate::ipc::rkyv_codec::encode_response(self);

        #[cfg(feature = "codec-flatbuf")]
        return crate::ipc::flatbuf_codec::encode_response(self);

        #[cfg(not(any(feature = "codec-rkyv", feature = "codec-flatbuf")))]
        match self {
            Self::RunResponse(output_ids) => Ok(encode_u32_slice(output_ids)),
            Self::TransferPrefillResponse(value)
            | Self::CheckPrefillStatusResponse(value)
            | Self::KvCacheSendResponse(value)
            | Self::KvCacheReleaseResponse(value)
            | Self::CheckKvCacheReleaseResponse(value)
            | Self::KvCacheSwapResponse(value) => {
                bincode::serialize(value).map_err(myelon_to_candle)
            }
            Self::ReceivePrefillResponse(value) => {
                bincode::serialize(value).map_err(myelon_to_candle)
            }
            Self::KvCacheReceiveResponse(value) => {
                bincode::serialize(value).map_err(myelon_to_candle)
            }
            Self::Error(error) => Ok(error.as_bytes().to_vec()),
        }
    }

    pub fn decode(kind: u8, payload: &[u8]) -> CandleResult<Self> {
        #[cfg(feature = "codec-rkyv")]
        return crate::ipc::rkyv_codec::decode_response(kind, payload);

        #[cfg(feature = "codec-flatbuf")]
        return crate::ipc::flatbuf_codec::decode_response(kind, payload);

        #[cfg(not(any(feature = "codec-rkyv", feature = "codec-flatbuf")))]
        match MsgKind::from_u8(kind)? {
            MsgKind::RunResponse => Ok(Self::RunResponse(decode_u32_slice(payload)?)),
            MsgKind::TransferPrefillResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::TransferPrefillResponse(value))
            }
            MsgKind::ReceivePrefillResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::ReceivePrefillResponse(value))
            }
            MsgKind::CheckPrefillStatusResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::CheckPrefillStatusResponse(value))
            }
            MsgKind::KvCacheSendResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheSendResponse(value))
            }
            MsgKind::KvCacheReceiveResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheReceiveResponse(value))
            }
            MsgKind::KvCacheReleaseResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheReleaseResponse(value))
            }
            MsgKind::CheckKvCacheReleaseResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::CheckKvCacheReleaseResponse(value))
            }
            MsgKind::KvCacheSwapResponse => {
                let value = bincode::deserialize(payload).map_err(myelon_to_candle)?;
                Ok(Self::KvCacheSwapResponse(value))
            }
            MsgKind::Error => Ok(Self::Error(String::from_utf8_lossy(payload).into_owned())),
            MsgKind::RunPrefill
            | MsgKind::RunDecode
            | MsgKind::FinishDecode
            | MsgKind::Cancel
            | MsgKind::Shutdown
            | MsgKind::TransferPrefill
            | MsgKind::ReceivePrefill
            | MsgKind::CheckPrefillStatus
            | MsgKind::KvCacheSend
            | MsgKind::KvCacheReceive
            | MsgKind::KvCacheRelease
            | MsgKind::CheckKvCacheRelease
            | MsgKind::KvCacheSwap
            | MsgKind::TypedRequest
            | MsgKind::TypedResponse => {
                candle_core::bail!("request kind {} is not a response", kind);
            }
        }
    }
}

pub struct MyelonEngineTransport {
    rpc_producer: RpcBroadcastProducer,
    response_consumers: Vec<ResponseConsumer>,
    access_mode: MyelonTransportAccessMode,
    /// Monotonic per-publish request id. Engine increments before each broadcast;
    /// runner echoes back into its response. Engine validates response.id == expected.
    next_request_id: AtomicU64,
    logged_first_request: bool,
    logged_first_response: bool,
}

impl MyelonEngineTransport {
    pub fn attach(
        runner_streams: &mut [LocalStream],
        session_label: &str,
        transport_config: MyelonTransportConfig,
    ) -> CandleResult<Self> {
        let layout = MyelonTransportLayout::for_session(
            session_label,
            runner_streams.len(),
            transport_config.rpc_depth,
            transport_config.response_depth,
        )
        .map_err(myelon_to_candle)?;
        let mmap_root_dir = match transport_config.backend {
            MyelonTransportBackend::Shm => None,
            MyelonTransportBackend::Mmap => {
                let root =
                    std::env::temp_dir().join(format!("vllm-rs-myelon-{}", layout.session_tag()));
                std::fs::create_dir_all(&root).map_err(myelon_to_candle)?;
                Some(root)
            }
        };
        let rpc_producer = match (transport_config.backend, transport_config.access_mode) {
            (MyelonTransportBackend::Shm, MyelonTransportAccessMode::Typed) => {
                RpcBroadcastProducer::create_typed_shm(layout.rpc_ring_name(), layout.rpc_depth())
            }
            (MyelonTransportBackend::Shm, _) => {
                RpcBroadcastProducer::create_shm(layout.rpc_ring_name(), layout.rpc_depth())
            }
            (MyelonTransportBackend::Mmap, MyelonTransportAccessMode::Typed) => {
                RpcBroadcastProducer::create_typed_mmap(
                    layout
                        .rpc_mmap_layout(mmap_root_dir.clone().expect("mmap root dir"))
                        .map_err(myelon_to_candle)?,
                    layout.rpc_depth(),
                )
            }
            (MyelonTransportBackend::Mmap, _) => RpcBroadcastProducer::create_mmap(
                layout
                    .rpc_mmap_layout(mmap_root_dir.clone().expect("mmap root dir"))
                    .map_err(myelon_to_candle)?,
                layout.rpc_depth(),
            ),
        }
        .map_err(myelon_to_candle)?;

        for (rank, stream) in runner_streams.iter_mut().enumerate() {
            let config = RunnerMyelonTransportConfig::for_rank(
                &layout,
                rank,
                &transport_config,
                mmap_root_dir.as_deref(),
            )?;
            send_local(
                &mut vec![stream.try_clone()?],
                &MessageType::InitMyelonTransport(config),
                false,
            )?;
            match receive_local(stream, false)? {
                MessageType::MyelonReady => {}
                other => {
                    candle_core::bail!("runner {} failed Myelon handoff: {:?}", rank, other);
                }
            }
        }

        let mut response_consumers = Vec::with_capacity(layout.runner_count());
        for rank in 0..layout.runner_count() {
            let consumer = match (transport_config.backend, transport_config.access_mode) {
                (MyelonTransportBackend::Shm, MyelonTransportAccessMode::Typed) => {
                    let response_ring_name =
                        layout.response_ring_name(rank).map_err(myelon_to_candle)?;
                    ResponseConsumer::attach_typed_shm(
                        response_ring_name,
                        layout.response_depth(),
                        transport_config.wait_strategy,
                    )
                }
                (MyelonTransportBackend::Shm, _) => {
                    let response_ring_name =
                        layout.response_ring_name(rank).map_err(myelon_to_candle)?;
                    ResponseConsumer::attach_shm(
                        response_ring_name,
                        layout.response_depth(),
                        transport_config.wait_strategy,
                    )
                }
                (MyelonTransportBackend::Mmap, MyelonTransportAccessMode::Typed) => {
                    ResponseConsumer::attach_typed_mmap(
                        layout
                            .response_mmap_layout(
                                mmap_root_dir.clone().expect("mmap root dir"),
                                rank,
                            )
                            .map_err(myelon_to_candle)?,
                        layout.response_depth(),
                        &format!("engine-response-{rank}"),
                        transport_config.wait_strategy,
                    )
                }
                (MyelonTransportBackend::Mmap, _) => ResponseConsumer::attach_mmap(
                    layout
                        .response_mmap_layout(mmap_root_dir.clone().expect("mmap root dir"), rank)
                        .map_err(myelon_to_candle)?,
                    layout.response_depth(),
                    &format!("engine-response-{rank}"),
                    transport_config.wait_strategy,
                ),
            }
            .map_err(myelon_to_candle)?;
            response_consumers.push(consumer);
        }

        Ok(Self {
            rpc_producer,
            response_consumers,
            access_mode: transport_config.access_mode,
            next_request_id: AtomicU64::new(1),
            logged_first_request: false,
            logged_first_response: false,
        })
    }

    pub fn run_prefill(&mut self, sequences: Vec<Sequence>) -> CandleResult<Vec<u32>> {
        self.publish_and_collect(&MyelonRequest::RunPrefill { sequences })
    }

    pub fn run_decode(&mut self, sequences: Vec<DecodeSequence>) -> CandleResult<Vec<u32>> {
        self.publish_and_collect(&MyelonRequest::RunDecode { sequences })
    }

    pub fn finish_decode(&mut self, sequence_id: usize) -> CandleResult<()> {
        self.publish_only(&MyelonRequest::FinishDecode { sequence_id })
            .map(|_| ())
    }

    pub fn transfer_prefill(&mut self, sequence: &Sequence) -> CandleResult<bool> {
        self.publish_and_collect_bool(
            &MyelonRequest::TransferPrefill {
                sequence: sequence.clone(),
            },
            |response| match response {
                MyelonResponse::TransferPrefillResponse(value) => Ok(value),
                other => {
                    candle_core::bail!("unexpected Myelon transfer_prefill response: {other:?}")
                }
            },
        )
    }

    pub fn receive_prefill(
        &mut self,
        available_tokens: usize,
    ) -> CandleResult<(bool, Option<Sequence>)> {
        self.publish_and_collect_value(
            &MyelonRequest::ReceivePrefill { available_tokens },
            |response| match response {
                MyelonResponse::ReceivePrefillResponse(value) => Ok(value),
                other => {
                    candle_core::bail!("unexpected Myelon receive_prefill response: {other:?}")
                }
            },
        )
    }

    pub fn check_prefill_status(&mut self, sequence_id: usize) -> CandleResult<bool> {
        self.publish_and_collect_bool(
            &MyelonRequest::CheckPrefillStatus { sequence_id },
            |response| match response {
                MyelonResponse::CheckPrefillStatusResponse(value) => Ok(value),
                other => {
                    candle_core::bail!("unexpected Myelon check_prefill_status response: {other:?}")
                }
            },
        )
    }

    pub fn send_kvcache(&mut self, sequence: &Sequence, first_token: u32) -> CandleResult<bool> {
        self.publish_and_collect_bool(
            &MyelonRequest::KvCacheSend {
                sequence: sequence.clone(),
                first_token,
            },
            |response| match response {
                MyelonResponse::KvCacheSendResponse(value) => Ok(value),
                other => candle_core::bail!("unexpected Myelon send_kvcache response: {other:?}"),
            },
        )
    }

    pub fn receive_kvcache(
        &mut self,
        sequence: &Sequence,
    ) -> CandleResult<(bool, u32, usize, usize)> {
        self.publish_and_collect_value(
            &MyelonRequest::KvCacheReceive {
                sequence: sequence.clone(),
            },
            |response| match response {
                MyelonResponse::KvCacheReceiveResponse(value) => Ok(value),
                other => {
                    candle_core::bail!("unexpected Myelon receive_kvcache response: {other:?}")
                }
            },
        )
    }

    pub fn release_remote_kvcache(&mut self, sequence_id: usize) -> CandleResult<bool> {
        self.publish_and_collect_bool(&MyelonRequest::KvCacheRelease { sequence_id }, |response| {
            match response {
                MyelonResponse::KvCacheReleaseResponse(value) => Ok(value),
                other => candle_core::bail!(
                    "unexpected Myelon release_remote_kvcache response: {other:?}"
                ),
            }
        })
    }

    pub fn check_kvcache_release(&mut self, sequence_id: usize) -> CandleResult<bool> {
        self.publish_and_collect_bool(
            &MyelonRequest::CheckKvCacheRelease { sequence_id },
            |response| match response {
                MyelonResponse::CheckKvCacheReleaseResponse(value) => Ok(value),
                other => candle_core::bail!(
                    "unexpected Myelon check_kvcache_release response: {other:?}"
                ),
            },
        )
    }

    pub fn swap_kvcache(
        &mut self,
        mappings: HashMap<usize, usize>,
        swap_in: bool,
    ) -> CandleResult<bool> {
        self.publish_and_collect_bool(
            &MyelonRequest::KvCacheSwap { mappings, swap_in },
            |response| match response {
                MyelonResponse::KvCacheSwapResponse(value) => Ok(value),
                other => candle_core::bail!("unexpected Myelon swap_kvcache response: {other:?}"),
            },
        )
    }

    pub fn shutdown(&mut self) {
        let _ = self
            .publish_only(&MyelonRequest::Shutdown)
            .expect("Myelon shutdown publish should succeed");
    }

    fn publish_only(&mut self, request: &MyelonRequest) -> CandleResult<(u64, PublishStats)> {
        let request_id = self.next_request_id.fetch_add(1, Ordering::Relaxed);
        if !self.logged_first_request {
            log_info!(
                "Dispatching first Myelon request kind={} request_id={}.",
                request.kind().as_u8(),
                request_id,
            );
            self.logged_first_request = true;
        }
        let stats = self.rpc_producer.publish_request(request, request_id)?;
        Ok((request_id, stats))
    }

    fn publish_and_collect(&mut self, request: &MyelonRequest) -> CandleResult<Vec<u32>> {
        let (request_id, publish_stats) = self.publish_only(request)?;
        self.collect_outputs(request_id, request.kind(), publish_stats)
    }

    fn publish_and_collect_value<T>(
        &mut self,
        request: &MyelonRequest,
        mut parse: impl FnMut(MyelonResponse) -> CandleResult<T>,
    ) -> CandleResult<T> {
        let (request_id, publish_stats) = self.publish_only(request)?;
        let request_kind = request.kind();
        let mut last_value: Option<T> = None;
        // Defer the FIRST error encountered while continuing to drain ALL N response
        // rings. This prevents per-rank response-ring drift: if we returned early on a
        // rank-0 Error/mismatch/parse-failure, ranks 1..N would leave their already-
        // published responses stranded in their rings, and the next call would read
        // those stale responses first → cascading correlation failures. See
        // 2_artifacts/2026-04-26_phase1_pd_msgid/REPORT.md "Phase 1.5".
        let mut deferred_error: Option<candle_core::Error> = None;
        let mut response_payload_bytes = 0usize;
        let mut collect_ns = 0u128;
        let mut decode_ns = 0u128;
        let mut response_count = 0usize;

        for (rank, consumer) in self.response_consumers.iter_mut().enumerate() {
            let recv: CandleResult<(ResponseRecvStats, MyelonResponse)> = match self.access_mode {
                MyelonTransportAccessMode::Owned => consumer.recv_response_blocking_owned(),
                MyelonTransportAccessMode::Typed => consumer.recv_response_blocking_typed(),
            };
            let (recv_stats, response) = match recv {
                Ok(pair) => pair,
                Err(e) => {
                    // Transport-level read failure — we cannot drain further on this
                    // consumer. Surface it as the first error if none yet.
                    if deferred_error.is_none() {
                        deferred_error = Some(candle_core::Error::Msg(format!(
                            "rank {rank} response read error: {e}"
                        )));
                    }
                    continue;
                }
            };
            response_count += 1;
            response_payload_bytes += recv_stats.payload_bytes;
            collect_ns += recv_stats.collect_ns;
            decode_ns += recv_stats.decode_ns;
            let response_id = recv_stats.request_id;
            if response_id != request_id {
                if deferred_error.is_none() {
                    deferred_error = Some(candle_core::Error::Msg(format!(
                        "Myelon response correlation mismatch on rank {rank}: expected \
                         request_id={request_id} (kind={request_kind:?}), got \
                         response_id={response_id} kind={:?}.",
                        response.kind(),
                    )));
                }
                continue;
            }
            if !self.logged_first_response {
                log_info!(
                    "Received first Myelon response kind={} request_id={}.",
                    response.kind().as_u8(),
                    response_id,
                );
                self.logged_first_response = true;
            }
            match response {
                MyelonResponse::Error(error) => {
                    if deferred_error.is_none() {
                        deferred_error = Some(candle_core::Error::Msg(format!(
                            "runner Myelon error: {error}"
                        )));
                    }
                }
                other => match parse(other) {
                    Ok(value) => last_value = Some(value),
                    Err(e) => {
                        if deferred_error.is_none() {
                            deferred_error = Some(e);
                        }
                    }
                },
            }
        }

        if let Some(error) = deferred_error {
            emit_ipc_instr(
                request_id,
                request_kind,
                self.access_mode,
                publish_stats.payload_bytes,
                response_payload_bytes,
                response_count,
                publish_stats.encode_ns,
                publish_stats.publish_ns,
                collect_ns,
                decode_ns,
                "error",
            );
            return Err(error);
        }
        let result = last_value
            .ok_or_else(|| candle_core::Error::Msg("missing Myelon runner response".to_string()));
        if result.is_ok() {
            emit_ipc_instr(
                request_id,
                request_kind,
                self.access_mode,
                publish_stats.payload_bytes,
                response_payload_bytes,
                response_count,
                publish_stats.encode_ns,
                publish_stats.publish_ns,
                collect_ns,
                decode_ns,
                "ok",
            );
        }
        result
    }

    fn publish_and_collect_bool(
        &mut self,
        request: &MyelonRequest,
        parse: impl FnMut(MyelonResponse) -> CandleResult<bool>,
    ) -> CandleResult<bool> {
        self.publish_and_collect_value(request, parse)
    }

    fn collect_outputs(
        &mut self,
        request_id: u64,
        request_kind: MsgKind,
        publish_stats: PublishStats,
    ) -> CandleResult<Vec<u32>> {
        let consumer = self
            .response_consumers
            .first_mut()
            .ok_or_else(|| candle_core::Error::Msg("missing Myelon runner response".to_string()))?;
        let (recv_stats, response) = match self.access_mode {
            MyelonTransportAccessMode::Owned => consumer.recv_response_blocking_owned()?,
            MyelonTransportAccessMode::Typed => consumer.recv_response_blocking_typed()?,
        };
        let response_id = recv_stats.request_id;
        if response_id != request_id {
            emit_ipc_instr(
                request_id,
                request_kind,
                self.access_mode,
                publish_stats.payload_bytes,
                recv_stats.payload_bytes,
                1,
                publish_stats.encode_ns,
                publish_stats.publish_ns,
                recv_stats.collect_ns,
                recv_stats.decode_ns,
                "error",
            );
            candle_core::bail!(
                "Myelon response correlation mismatch on rank 0: expected request_id={} (kind={:?}), got response_id={} kind={:?}.",
                request_id,
                request_kind,
                response_id,
                response.kind(),
            );
        }
        if !self.logged_first_response {
            log_info!(
                "Received first Myelon response kind={} request_id={}.",
                response.kind().as_u8(),
                response_id,
            );
            self.logged_first_response = true;
        }
        match response {
            MyelonResponse::RunResponse(output_ids) => {
                emit_ipc_instr(
                    request_id,
                    request_kind,
                    self.access_mode,
                    publish_stats.payload_bytes,
                    recv_stats.payload_bytes,
                    1,
                    publish_stats.encode_ns,
                    publish_stats.publish_ns,
                    recv_stats.collect_ns,
                    recv_stats.decode_ns,
                    "ok",
                );
                Ok(output_ids)
            }
            MyelonResponse::Error(error) => {
                emit_ipc_instr(
                    request_id,
                    request_kind,
                    self.access_mode,
                    publish_stats.payload_bytes,
                    recv_stats.payload_bytes,
                    1,
                    publish_stats.encode_ns,
                    publish_stats.publish_ns,
                    recv_stats.collect_ns,
                    recv_stats.decode_ns,
                    "error",
                );
                candle_core::bail!("runner Myelon error: {}", error);
            }
            other => {
                emit_ipc_instr(
                    request_id,
                    request_kind,
                    self.access_mode,
                    publish_stats.payload_bytes,
                    recv_stats.payload_bytes,
                    1,
                    publish_stats.encode_ns,
                    publish_stats.publish_ns,
                    recv_stats.collect_ns,
                    recv_stats.decode_ns,
                    "error",
                );
                candle_core::bail!("unexpected Myelon run response: {other:?}");
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(feature = "codec-rkyv")]
    use crate::utils::config::SamplingParams;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    use myelon_playground::{frame_flags, publish_framed_payload, transport::FramedTransportFrame};

    static UNIQUE_SUFFIX: AtomicU64 = AtomicU64::new(0);

    fn unique_ring_name(prefix: &str) -> String {
        let counter = UNIQUE_SUFFIX.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be valid")
            .as_nanos();
        format!("{prefix}{:02x}{:08x}", (counter & 0xff) as u8, nanos as u32)
    }

    #[test]
    fn segmented_frame_flags_mark_boundaries() {
        assert_eq!(frame_flags(true, true), 0b11);
        assert_eq!(frame_flags(true, false), 0b01);
        assert_eq!(frame_flags(false, true), 0b10);
        assert_eq!(frame_flags(false, false), 0b00);
    }

    #[test]
    fn publish_frames_splits_large_payload() {
        let payload = vec![7u8; RPC_FRAME_DATA_BYTES * 2 + 17];
        let mut frames = Vec::new();

        publish_framed_payload(
            &payload,
            MsgKind::RunDecode.as_u8(),
            RPC_FRAME_DATA_BYTES,
            |frame| frames.push(frame),
            |chunk, kind, msg_id, flags| {
                let mut frame = RpcFrame::default();
                frame.write_frame(chunk, kind, msg_id, flags);
                frame
            },
        );

        assert_eq!(frames.len(), 3);
        assert_eq!(frames[0].flags, 0b01);
        assert_eq!(frames[1].flags, 0b00);
        assert_eq!(frames[2].flags, 0b10);
        assert_eq!(frames[0].kind, MsgKind::RunDecode.as_u8());
        assert_eq!(frames[0].msg_id, frames[1].msg_id);
        assert_eq!(frames[1].msg_id, frames[2].msg_id);
    }

    #[test]
    fn rpc_consumer_sees_coordination_cursor_while_producer_lives() {
        let ring_name = unique_ring_name("vmyrpc");
        let producer = RpcBroadcastProducer::create_shm(&ring_name, 8).unwrap();
        let consumer =
            RpcBroadcastConsumer::attach_shm(&ring_name, 8, MyelonWaitStrategy::Block).unwrap();

        assert!(consumer.has_coordination_support());

        drop(producer);
    }

    #[test]
    fn response_consumer_sees_coordination_cursor_while_producer_lives() {
        let ring_name = unique_ring_name("vmyrsp");
        let producer = ResponseProducer::create_shm(&ring_name, 8).unwrap();
        let consumer =
            ResponseConsumer::attach_shm(&ring_name, 8, MyelonWaitStrategy::Block).unwrap();

        assert!(consumer.has_coordination_support());

        drop(producer);
    }

    #[test]
    fn request_round_trip_preserves_existing_prefill_wire_contract() {
        let request = MyelonRequest::RunPrefill {
            sequences: Vec::new(),
        };
        let bytes = request.encode().unwrap();
        let decoded = MyelonRequest::decode(MsgKind::RunPrefill.as_u8(), &bytes).unwrap();

        match decoded {
            MyelonRequest::RunPrefill { sequences } => assert!(sequences.is_empty()),
            other => panic!("unexpected request: {other:?}"),
        }
    }

    #[test]
    fn prepend_split_request_id_round_trip() {
        let id: u64 = 0xDEAD_BEEF_CAFE_F00D;
        let payload = b"hello-myelon".as_slice();
        let stamped = prepend_request_id(id, payload);
        assert_eq!(stamped.len(), REQUEST_ID_BYTES + payload.len());
        let (recovered_id, body) = split_request_id(&stamped).expect("valid prefix");
        assert_eq!(recovered_id, id);
        assert_eq!(body, payload);
    }

    #[test]
    fn split_request_id_rejects_short_buffer() {
        let err = split_request_id(&[1, 2, 3]).unwrap_err().to_string();
        assert!(
            err.contains("too short for request_id prefix"),
            "got: {err}"
        );
    }

    #[cfg(feature = "codec-rkyv")]
    #[test]
    fn rkyv_request_decode_survives_misaligned_prefill_payload() {
        let request = MyelonRequest::RunPrefill {
            sequences: vec![crate::core::sequence::Sequence::new(
                vec![1, 2, 3, 4, 5, 6, 7, 8],
                16,
                SamplingParams::default(),
                &None,
                0,
            )],
        };
        let bytes = request.encode().unwrap();
        let mut misaligned = Vec::with_capacity(bytes.len() + 1);
        misaligned.push(0);
        misaligned.extend_from_slice(&bytes);

        let decoded = MyelonRequest::decode(MsgKind::RunPrefill.as_u8(), &misaligned[1..]).unwrap();

        match decoded {
            MyelonRequest::RunPrefill { sequences } => {
                assert_eq!(sequences.len(), 1);
                assert_eq!(sequences[0].token_ids, vec![1, 2, 3, 4, 5, 6, 7, 8]);
            }
            other => panic!("unexpected request: {other:?}"),
        }
    }

    #[cfg(feature = "codec-rkyv")]
    #[test]
    fn rkyv_request_decode_survives_large_misaligned_prefill_payload() {
        let mut sequences = Vec::new();
        for sequence_id in 0..8usize {
            let token_ids = (0..1700u32)
                .map(|token| token + sequence_id as u32)
                .collect();
            let mut sequence = crate::core::sequence::Sequence::new(
                token_ids,
                16,
                SamplingParams::default(),
                &None,
                0,
            );
            sequence.id = sequence_id;
            sequences.push(sequence);
        }

        let request = MyelonRequest::RunPrefill { sequences };
        let bytes = request.encode().unwrap();
        assert!(
            bytes.len() > 50_000,
            "expected large payload, got {}",
            bytes.len()
        );
        let mut misaligned = Vec::with_capacity(bytes.len() + 1);
        misaligned.push(0);
        misaligned.extend_from_slice(&bytes);

        let decoded = MyelonRequest::decode(MsgKind::RunPrefill.as_u8(), &misaligned[1..]).unwrap();

        match decoded {
            MyelonRequest::RunPrefill { sequences } => {
                assert_eq!(sequences.len(), 8);
                assert_eq!(sequences[0].token_ids.len(), 1700);
                assert_eq!(sequences[7].token_ids.len(), 1700);
            }
            other => panic!("unexpected request: {other:?}"),
        }
    }

    #[test]
    fn shutdown_request_requires_empty_payload() {
        let error = MyelonRequest::decode(MsgKind::Shutdown.as_u8(), &[1, 2]).unwrap_err();
        assert!(error
            .to_string()
            .contains("Shutdown request must not carry a payload"));
    }

    #[test]
    fn response_round_trip_preserves_output_payloads() {
        let response = MyelonResponse::RunResponse(vec![1, 2, 3]);
        let bytes = response.encode().unwrap();
        let decoded = MyelonResponse::decode(MsgKind::RunResponse.as_u8(), &bytes).unwrap();

        match decoded {
            MyelonResponse::RunResponse(output_ids) => assert_eq!(output_ids, vec![1, 2, 3]),
            other => panic!("unexpected response: {other:?}"),
        }
    }

    #[test]
    fn request_kind_rejects_response_payloads() {
        let error = MyelonRequest::decode(MsgKind::Error.as_u8(), b"boom").unwrap_err();
        assert!(error.to_string().contains("is not a request"));
    }
}
