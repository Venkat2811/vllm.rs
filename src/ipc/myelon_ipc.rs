use anyhow::{Context, Result};
use candle_core::Result as CandleResult;
use interprocess::local_socket::Stream as LocalStream;
use interprocess::TryClone;
use myelon_playground::transport::{
    FixedFrame, FramedTransportConsumer, FramedTransportProducer, MmapFramedTransportConsumer,
    MmapFramedTransportProducer, ReassemblyBuffer,
};
pub use myelon_playground::{MyelonTransportLayout, MyelonWaitStrategy};
use std::collections::HashMap;
use std::path::Path;

use myelon_playground::MmapTransportLayout;
use serde::{Deserialize, Serialize};

use crate::core::sequence::{DecodeSequence, Sequence};
use crate::log_info;
use crate::runner::{receive_local, send_local, MessageType};

pub const RPC_FRAME_HEADER_BYTES: usize = 12;
pub const RESPONSE_FRAME_HEADER_BYTES: usize = 12;
pub const RPC_FRAME_DATA_BYTES: usize = 64 * 1024 - RPC_FRAME_HEADER_BYTES;
pub const RESPONSE_FRAME_DATA_BYTES: usize = 4 * 1024 - RESPONSE_FRAME_HEADER_BYTES;
pub const VLLM_RS_DEFAULT_MYELON_RPC_DEPTH: usize = 8192;
pub const VLLM_RS_DEFAULT_MYELON_RESPONSE_DEPTH: usize = 8192;

pub type RpcFrame = FixedFrame<RPC_FRAME_DATA_BYTES>;
pub type ResponseFrame = FixedFrame<RESPONSE_FRAME_DATA_BYTES>;

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
    Borrowed,
}

impl MyelonTransportAccessMode {
    pub fn parse(value: Option<&str>) -> CandleResult<Self> {
        match value.unwrap_or("owned") {
            "owned" => Ok(Self::Owned),
            "borrowed" => Ok(Self::Borrowed),
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
    Shm { inner: FramedTransportProducer<RpcFrame> },
    Mmap { inner: MmapFramedTransportProducer<RpcFrame> },
}

impl RpcBroadcastProducer {
    pub fn create_shm(name: &str, depth: usize) -> Result<Self> {
        let inner = FramedTransportProducer::<RpcFrame>::create(name, depth)
            .with_context(|| format!("failed to create rpc ring '{name}'"))?;
        Ok(Self::Shm { inner })
    }

    pub fn create_mmap(layout: MmapTransportLayout, depth: usize) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapFramedTransportProducer::<RpcFrame>::create(layout, depth)
            .with_context(|| format!("failed to create mmap rpc ring '{segment}'"))?;
        Ok(Self::Mmap { inner })
    }

    pub fn publish(&mut self, payload: &[u8], kind: MsgKind) {
        match self {
            Self::Shm { inner } => inner.publish(payload, kind.as_u8()),
            Self::Mmap { inner } => inner.publish(payload, kind.as_u8()),
        }
    }

    pub fn publish_request(&mut self, request: &MyelonRequest) -> CandleResult<Vec<u8>> {
        let bytes = request.encode()?;
        self.publish(&bytes, request.kind());
        Ok(bytes)
    }
}

pub enum RpcBroadcastConsumer {
    Shm {
        inner: FramedTransportConsumer<RpcFrame>,
        reassembly: ReassemblyBuffer,
    },
    Mmap {
        inner: MmapFramedTransportConsumer<RpcFrame>,
        reassembly: ReassemblyBuffer,
    },
}

impl RpcBroadcastConsumer {
    pub fn attach_shm(name: &str, depth: usize, wait_strategy: MyelonWaitStrategy) -> Result<Self> {
        let inner = FramedTransportConsumer::<RpcFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach rpc ring '{name}'"))?;
        Ok(Self::Shm {
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
        let inner =
            MmapFramedTransportConsumer::<RpcFrame>::attach(layout, depth, consumer_id, wait_strategy)
                .with_context(|| format!("failed to attach mmap rpc ring '{segment}'"))?;
        Ok(Self::Mmap {
            inner,
            reassembly: ReassemblyBuffer::new(RPC_FRAME_DATA_BYTES),
        })
    }

    pub fn has_coordination_support(&self) -> bool {
        match self {
            Self::Shm { inner, .. } => inner.has_coordination_support(),
            Self::Mmap { inner, .. } => inner.has_coordination_support(),
        }
    }

    pub fn recv_request_blocking_owned(&mut self) -> CandleResult<MyelonRequest> {
        match self {
            Self::Shm { inner, .. } => {
                let (kind, payload) = inner.recv_message_blocking_owned();
                MyelonRequest::decode(kind, &payload)
            }
            Self::Mmap { inner, .. } => {
                let (kind, payload) = inner.recv_message_blocking_owned();
                MyelonRequest::decode(kind, &payload)
            }
        }
    }

    pub fn recv_request_blocking_borrowed(&mut self) -> CandleResult<MyelonRequest> {
        match self {
            Self::Shm { inner, reassembly } => inner
                .recv_message_blocking_leased(reassembly, MyelonRequest::decode),
            Self::Mmap { inner, reassembly } => inner
                .recv_message_blocking_leased(reassembly, MyelonRequest::decode),
        }
    }
}

pub enum ResponseProducer {
    Shm { inner: FramedTransportProducer<ResponseFrame> },
    Mmap { inner: MmapFramedTransportProducer<ResponseFrame> },
}

impl ResponseProducer {
    pub fn create_shm(name: &str, depth: usize) -> Result<Self> {
        let inner = FramedTransportProducer::<ResponseFrame>::create(name, depth)
            .with_context(|| format!("failed to create response ring '{name}'"))?;
        Ok(Self::Shm { inner })
    }

    pub fn create_mmap(layout: MmapTransportLayout, depth: usize) -> Result<Self> {
        let segment = layout.segment_name().to_string();
        let inner = MmapFramedTransportProducer::<ResponseFrame>::create(layout, depth)
            .with_context(|| format!("failed to create mmap response ring '{segment}'"))?;
        Ok(Self::Mmap { inner })
    }

    pub fn send(&mut self, payload: &[u8], kind: MsgKind) {
        match self {
            Self::Shm { inner } => inner.publish(payload, kind.as_u8()),
            Self::Mmap { inner } => inner.publish(payload, kind.as_u8()),
        }
    }

    pub fn send_response(&mut self, response: &MyelonResponse) -> CandleResult<Vec<u8>> {
        let bytes = response.encode()?;
        self.send(&bytes, response.kind());
        Ok(bytes)
    }

    pub fn send_error(&mut self, error: impl std::fmt::Display) {
        let response = MyelonResponse::Error(error.to_string());
        let bytes = response
            .encode()
            .expect("MyelonResponse::Error should always serialize");
        self.send(&bytes, response.kind());
    }
}

pub enum ResponseConsumer {
    Shm {
        inner: FramedTransportConsumer<ResponseFrame>,
        reassembly: ReassemblyBuffer,
    },
    Mmap {
        inner: MmapFramedTransportConsumer<ResponseFrame>,
        reassembly: ReassemblyBuffer,
    },
}

impl ResponseConsumer {
    pub fn attach_shm(
        name: &str,
        depth: usize,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        let inner = FramedTransportConsumer::<ResponseFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach response ring '{name}'"))?;
        Ok(Self::Shm {
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
        Ok(Self::Mmap {
            inner,
            reassembly: ReassemblyBuffer::new(RESPONSE_FRAME_DATA_BYTES),
        })
    }

    pub fn has_coordination_support(&self) -> bool {
        match self {
            Self::Shm { inner, .. } => inner.has_coordination_support(),
            Self::Mmap { inner, .. } => inner.has_coordination_support(),
        }
    }

    pub fn recv_response_blocking_owned(&mut self) -> CandleResult<MyelonResponse> {
        match self {
            Self::Shm { inner, .. } => {
                let (kind, payload) = inner.recv_message_blocking_owned();
                MyelonResponse::decode(kind, &payload)
            }
            Self::Mmap { inner, .. } => {
                let (kind, payload) = inner.recv_message_blocking_owned();
                MyelonResponse::decode(kind, &payload)
            }
        }
    }

    pub fn recv_response_blocking_borrowed(&mut self) -> CandleResult<MyelonResponse> {
        match self {
            Self::Shm { inner, reassembly } => inner
                .recv_message_blocking_leased(reassembly, MyelonResponse::decode),
            Self::Mmap { inner, reassembly } => inner
                .recv_message_blocking_leased(reassembly, MyelonResponse::decode),
        }
    }
}

#[derive(Debug)]
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
            | MsgKind::KvCacheSwapResponse => {
                candle_core::bail!("response kind {} is not a request", kind);
            }
        }
    }
}

#[derive(Debug)]
pub enum MyelonResponse {
    RunResponse(Vec<u32>),
    TransferPrefillResponse(bool),
    ReceivePrefillResponse((bool, Option<Sequence>)),
    CheckPrefillStatusResponse(bool),
    KvCacheSendResponse(bool),
    KvCacheReceiveResponse((bool, u32, usize)),
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
            | MsgKind::KvCacheSwap => {
                candle_core::bail!("request kind {} is not a response", kind);
            }
        }
    }
}

pub struct MyelonEngineTransport {
    rpc_producer: RpcBroadcastProducer,
    response_consumers: Vec<ResponseConsumer>,
    access_mode: MyelonTransportAccessMode,
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
                let root = std::env::temp_dir()
                    .join(format!("vllm-rs-myelon-{}", layout.session_tag()));
                std::fs::create_dir_all(&root).map_err(myelon_to_candle)?;
                Some(root)
            }
        };
        let rpc_producer = match transport_config.backend {
            MyelonTransportBackend::Shm => {
                RpcBroadcastProducer::create_shm(layout.rpc_ring_name(), layout.rpc_depth())
            }
            MyelonTransportBackend::Mmap => RpcBroadcastProducer::create_mmap(
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
            let consumer = match transport_config.backend {
                MyelonTransportBackend::Shm => {
                    let response_ring_name =
                        layout.response_ring_name(rank).map_err(myelon_to_candle)?;
                    ResponseConsumer::attach_shm(
                        response_ring_name,
                        layout.response_depth(),
                        transport_config.wait_strategy,
                    )
                }
                MyelonTransportBackend::Mmap => ResponseConsumer::attach_mmap(
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

    pub fn receive_kvcache(&mut self, sequence: &Sequence) -> CandleResult<(bool, u32, usize)> {
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
        self.rpc_producer.publish(&[], MsgKind::Shutdown);
    }

    fn publish_only(&mut self, request: &MyelonRequest) -> CandleResult<()> {
        let bytes = request.encode()?;
        if !self.logged_first_request {
            log_info!(
                "Dispatching first Myelon request kind={} bytes={}.",
                request.kind().as_u8(),
                bytes.len()
            );
            self.logged_first_request = true;
        }
        self.rpc_producer.publish(&bytes, request.kind());
        Ok(())
    }

    fn publish_and_collect(&mut self, request: &MyelonRequest) -> CandleResult<Vec<u32>> {
        self.publish_only(request)?;
        self.collect_outputs()
    }

    fn publish_and_collect_value<T>(
        &mut self,
        request: &MyelonRequest,
        mut parse: impl FnMut(MyelonResponse) -> CandleResult<T>,
    ) -> CandleResult<T> {
        self.publish_only(request)?;
        let mut last_value: Option<T> = None;

        for consumer in &mut self.response_consumers {
            let response = match self.access_mode {
                MyelonTransportAccessMode::Owned => consumer.recv_response_blocking_owned()?,
                MyelonTransportAccessMode::Borrowed => consumer.recv_response_blocking_borrowed()?,
            };
            if !self.logged_first_response {
                log_info!(
                    "Received first Myelon response kind={} bytes={}.",
                    response.kind().as_u8(),
                    response.encode()?.len()
                );
                self.logged_first_response = true;
            }
            let value = match response {
                MyelonResponse::Error(error) => {
                    candle_core::bail!("runner Myelon error: {}", error);
                }
                other => parse(other)?,
            };
            last_value = Some(value);
        }

        last_value
            .ok_or_else(|| candle_core::Error::Msg("missing Myelon runner response".to_string()))
    }

    fn publish_and_collect_bool(
        &mut self,
        request: &MyelonRequest,
        parse: impl FnMut(MyelonResponse) -> CandleResult<bool>,
    ) -> CandleResult<bool> {
        self.publish_and_collect_value(request, parse)
    }

    fn collect_outputs(&mut self) -> CandleResult<Vec<u32>> {
        let consumer = self
            .response_consumers
            .first_mut()
            .ok_or_else(|| candle_core::Error::Msg("missing Myelon runner response".to_string()))?;
        let response = match self.access_mode {
            MyelonTransportAccessMode::Owned => consumer.recv_response_blocking_owned()?,
            MyelonTransportAccessMode::Borrowed => consumer.recv_response_blocking_borrowed()?,
        };
        if !self.logged_first_response {
            log_info!(
                "Received first Myelon response kind={} bytes={}.",
                response.kind().as_u8(),
                response.encode()?.len()
            );
            self.logged_first_response = true;
        }
        match response {
            MyelonResponse::RunResponse(output_ids) => Ok(output_ids),
            MyelonResponse::Error(error) => {
                candle_core::bail!("runner Myelon error: {}", error);
            }
            other => {
                candle_core::bail!("unexpected Myelon run response: {other:?}");
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
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
        format!("{prefix}{counter:x}{nanos:x}")
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
            let token_ids = (0..1700u32).map(|token| token + sequence_id as u32).collect();
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
        assert!(bytes.len() > 50_000, "expected large payload, got {}", bytes.len());
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
