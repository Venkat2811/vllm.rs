use anyhow::{Context, Result};
use candle_core::Result as CandleResult;
use interprocess::local_socket::Stream as LocalStream;
use interprocess::TryClone;
use myelon_playground::transport::{FixedFrame, FramedTransportConsumer, FramedTransportProducer};
pub use myelon_playground::{
    MyelonTransportConfig, MyelonTransportLayout, MyelonWaitStrategy, RunnerMyelonTransportConfig,
};
use std::collections::HashMap;

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

fn encode_u32_slice(values: &[u32]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(4 + values.len() * std::mem::size_of::<u32>());
    bytes.extend_from_slice(&(values.len() as u32).to_le_bytes());
    for value in values {
        bytes.extend_from_slice(&value.to_le_bytes());
    }
    bytes
}

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
    )
    .map_err(myelon_to_candle)
}

pub struct RpcBroadcastProducer {
    inner: FramedTransportProducer<RpcFrame>,
}

impl RpcBroadcastProducer {
    pub fn create(name: &str, depth: usize) -> Result<Self> {
        let inner = FramedTransportProducer::<RpcFrame>::create(name, depth)
            .with_context(|| format!("failed to create rpc ring '{name}'"))?;
        Ok(Self { inner })
    }

    pub fn publish(&mut self, payload: &[u8], kind: MsgKind) {
        self.inner.publish(payload, kind.as_u8());
    }

    pub fn publish_request(&mut self, request: &MyelonRequest) -> CandleResult<Vec<u8>> {
        let bytes = request.encode()?;
        self.publish(&bytes, request.kind());
        Ok(bytes)
    }
}

pub struct RpcBroadcastConsumer {
    inner: FramedTransportConsumer<RpcFrame>,
}

impl RpcBroadcastConsumer {
    pub fn attach(name: &str, depth: usize, wait_strategy: MyelonWaitStrategy) -> Result<Self> {
        let inner = FramedTransportConsumer::<RpcFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach rpc ring '{name}'"))?;
        Ok(Self { inner })
    }

    pub fn has_coordination_support(&self) -> bool {
        self.inner.has_coordination_support()
    }

    pub fn recv_message_blocking(&mut self) -> (u8, Vec<u8>) {
        self.inner.recv_message_blocking()
    }

    pub fn recv_request_blocking(&mut self) -> CandleResult<MyelonRequest> {
        let (kind, payload) = self.recv_message_blocking();
        MyelonRequest::decode(kind, &payload)
    }
}

pub struct ResponseProducer {
    inner: FramedTransportProducer<ResponseFrame>,
}

impl ResponseProducer {
    pub fn create(name: &str, depth: usize) -> Result<Self> {
        let inner = FramedTransportProducer::<ResponseFrame>::create(name, depth)
            .with_context(|| format!("failed to create response ring '{name}'"))?;
        Ok(Self { inner })
    }

    pub fn send(&mut self, payload: &[u8], kind: MsgKind) {
        self.inner.publish(payload, kind.as_u8());
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

pub struct ResponseConsumer {
    inner: FramedTransportConsumer<ResponseFrame>,
}

impl ResponseConsumer {
    pub fn attach(name: &str, depth: usize, wait_strategy: MyelonWaitStrategy) -> Result<Self> {
        let inner = FramedTransportConsumer::<ResponseFrame>::attach(name, depth, wait_strategy)
            .with_context(|| format!("failed to attach response ring '{name}'"))?;
        Ok(Self { inner })
    }

    pub fn has_coordination_support(&self) -> bool {
        self.inner.has_coordination_support()
    }

    pub fn recv_message_blocking(&mut self) -> (u8, Vec<u8>) {
        self.inner.recv_message_blocking()
    }

    pub fn recv_response_blocking(&mut self) -> CandleResult<MyelonResponse> {
        let (kind, payload) = self.recv_message_blocking();
        MyelonResponse::decode(kind, &payload)
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
    logged_first_request: bool,
    logged_first_response: bool,
    logged_rank_divergence_warning: bool,
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
        let rpc_producer = RpcBroadcastProducer::create(layout.rpc_ring_name(), layout.rpc_depth())
            .map_err(myelon_to_candle)?;

        for (rank, stream) in runner_streams.iter_mut().enumerate() {
            let config = RunnerMyelonTransportConfig::for_rank(
                &layout,
                rank,
                transport_config.wait_strategy,
            )
            .map_err(myelon_to_candle)?;
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
            let response_ring_name = layout.response_ring_name(rank).map_err(myelon_to_candle)?;
            let consumer = ResponseConsumer::attach(
                response_ring_name,
                layout.response_depth(),
                transport_config.wait_strategy,
            )
            .map_err(myelon_to_candle)?;
            response_consumers.push(consumer);
        }

        Ok(Self {
            rpc_producer,
            response_consumers,
            logged_first_request: false,
            logged_first_response: false,
            logged_rank_divergence_warning: false,
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
            let response = consumer.recv_response_blocking()?;
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
        let mut last_output: Option<Vec<u32>> = None;

        for consumer in &mut self.response_consumers {
            let response = consumer.recv_response_blocking()?;
            if !self.logged_first_response {
                log_info!(
                    "Received first Myelon response kind={} bytes={}.",
                    response.kind().as_u8(),
                    response.encode()?.len()
                );
                self.logged_first_response = true;
            }
            match response {
                MyelonResponse::RunResponse(output_ids) => {
                    if let Some(expected) = &last_output {
                        if expected != &output_ids && !self.logged_rank_divergence_warning {
                            log_info!(
                                "Myelon runner outputs differed across ranks; keeping the last response to match legacy process-runner behavior."
                            );
                            self.logged_rank_divergence_warning = true;
                        }
                    }
                    last_output = Some(output_ids);
                }
                MyelonResponse::Error(error) => {
                    candle_core::bail!("runner Myelon error: {}", error);
                }
                other => {
                    candle_core::bail!("unexpected Myelon run response: {other:?}");
                }
            }
        }

        last_output
            .ok_or_else(|| candle_core::Error::Msg("missing Myelon runner response".to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
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
        let producer = RpcBroadcastProducer::create(&ring_name, 8).unwrap();
        let consumer =
            RpcBroadcastConsumer::attach(&ring_name, 8, MyelonWaitStrategy::Block).unwrap();

        assert!(consumer.has_coordination_support());

        drop(producer);
    }

    #[test]
    fn response_consumer_sees_coordination_cursor_while_producer_lives() {
        let ring_name = unique_ring_name("vmyrsp");
        let producer = ResponseProducer::create(&ring_name, 8).unwrap();
        let consumer = ResponseConsumer::attach(&ring_name, 8, MyelonWaitStrategy::Block).unwrap();

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

        assert_eq!(decoded, response);
    }

    #[test]
    fn request_kind_rejects_response_payloads() {
        let error = MyelonRequest::decode(MsgKind::Error.as_u8(), b"boom").unwrap_err();
        assert!(error.to_string().contains("is not a request"));
    }
}
