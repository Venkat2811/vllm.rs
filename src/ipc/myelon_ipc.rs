use anyhow::{Context, Result};
use candle_core::Result as CandleResult;
use interprocess::local_socket::Stream as LocalStream;
use interprocess::TryClone;
use myelon_playground::transport::{
    FramedTransportConsumer, FramedTransportFrame, FramedTransportProducer,
};
pub use myelon_playground::{
    FrameMeta, MyelonTransportLayout, MyelonWaitStrategy, RunnerMyelonTransportConfig,
};
use serde::Serialize;

use crate::core::sequence::{DecodeSequence, Sequence};
use crate::log_info;
use crate::runner::{receive_local, send_local, MessageType};

pub const RPC_FRAME_HEADER_BYTES: usize = 12;
pub const RESPONSE_FRAME_HEADER_BYTES: usize = 12;
pub const RPC_FRAME_DATA_BYTES: usize = 64 * 1024 - RPC_FRAME_HEADER_BYTES;
pub const RESPONSE_FRAME_DATA_BYTES: usize = 4 * 1024 - RESPONSE_FRAME_HEADER_BYTES;

#[repr(C)]
#[derive(Copy, Clone)]
pub struct RpcFrame {
    pub len: u32,
    pub kind: u8,
    pub flags: u8,
    pub msg_id: u32,
    pub data: [u8; RPC_FRAME_DATA_BYTES],
}

impl Default for RpcFrame {
    fn default() -> Self {
        Self {
            len: 0,
            kind: 0,
            flags: 0,
            msg_id: 0,
            data: [0u8; RPC_FRAME_DATA_BYTES],
        }
    }
}

impl FramedTransportFrame for RpcFrame {
    fn payload_capacity() -> usize {
        RPC_FRAME_DATA_BYTES
    }

    fn frame_meta(&self) -> FrameMeta<'_> {
        FrameMeta {
            len: self.len as usize,
            kind: self.kind,
            flags: self.flags,
            msg_id: self.msg_id,
            data: &self.data[..self.len as usize],
        }
    }

    fn write_frame(&mut self, payload: &[u8], kind: u8, msg_id: u32, flags: u8) {
        self.len = payload.len() as u32;
        self.kind = kind;
        self.flags = flags;
        self.msg_id = msg_id;
        self.data[..payload.len()].copy_from_slice(payload);
    }
}

#[repr(C)]
#[derive(Copy, Clone)]
pub struct ResponseFrame {
    pub len: u32,
    pub kind: u8,
    pub flags: u8,
    pub msg_id: u32,
    pub data: [u8; RESPONSE_FRAME_DATA_BYTES],
}

impl Default for ResponseFrame {
    fn default() -> Self {
        Self {
            len: 0,
            kind: 0,
            flags: 0,
            msg_id: 0,
            data: [0u8; RESPONSE_FRAME_DATA_BYTES],
        }
    }
}

impl FramedTransportFrame for ResponseFrame {
    fn payload_capacity() -> usize {
        RESPONSE_FRAME_DATA_BYTES
    }

    fn frame_meta(&self) -> FrameMeta<'_> {
        FrameMeta {
            len: self.len as usize,
            kind: self.kind,
            flags: self.flags,
            msg_id: self.msg_id,
            data: &self.data[..self.len as usize],
        }
    }

    fn write_frame(&mut self, payload: &[u8], kind: u8, msg_id: u32, flags: u8) {
        self.len = payload.len() as u32;
        self.kind = kind;
        self.flags = flags;
        self.msg_id = msg_id;
        self.data[..payload.len()].copy_from_slice(payload);
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
    RunResponse = 100,
    Error = 101,
}

impl MsgKind {
    pub const fn as_u8(self) -> u8 {
        self as u8
    }
}

const MYELON_RPC_DEPTH: usize = 1024;
const MYELON_RESPONSE_DEPTH: usize = 256;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ResolvedMyelonTransportConfig {
    pub rpc_depth: usize,
    pub response_depth: usize,
    pub wait_strategy: MyelonWaitStrategy,
}

fn myelon_to_candle<E: std::fmt::Display>(error: E) -> candle_core::Error {
    candle_core::Error::Msg(error.to_string())
}

pub fn resolve_myelon_transport_config(
    rpc_depth: Option<usize>,
    response_depth: Option<usize>,
    busy_spin: Option<bool>,
) -> CandleResult<ResolvedMyelonTransportConfig> {
    let rpc_depth = rpc_depth.unwrap_or(MYELON_RPC_DEPTH);
    if rpc_depth == 0 {
        candle_core::bail!("myelon_rpc_depth must be greater than zero");
    }

    let response_depth = response_depth.unwrap_or(MYELON_RESPONSE_DEPTH);
    if response_depth == 0 {
        candle_core::bail!("myelon_response_depth must be greater than zero");
    }

    let wait_strategy = if busy_spin.unwrap_or(false) {
        MyelonWaitStrategy::BusySpin
    } else {
        MyelonWaitStrategy::Block
    };

    Ok(ResolvedMyelonTransportConfig {
        rpc_depth,
        response_depth,
        wait_strategy,
    })
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
}

pub struct MyelonEngineTransport {
    rpc_producer: RpcBroadcastProducer,
    response_consumers: Vec<ResponseConsumer>,
    logged_first_request: bool,
    logged_first_response: bool,
}

impl MyelonEngineTransport {
    pub fn attach(
        runner_streams: &mut [LocalStream],
        session_label: &str,
        transport_config: ResolvedMyelonTransportConfig,
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
        })
    }

    pub fn run_prefill(&mut self, sequences: Vec<Sequence>) -> CandleResult<Vec<u32>> {
        self.publish_and_collect(&(sequences, true), MsgKind::RunPrefill)
    }

    pub fn run_decode(&mut self, sequences: Vec<DecodeSequence>) -> CandleResult<Vec<u32>> {
        self.publish_and_collect(&(sequences, false), MsgKind::RunDecode)
    }

    pub fn finish_decode(&mut self, sequence_id: usize) -> CandleResult<()> {
        self.publish_only(&sequence_id, MsgKind::FinishDecode)
    }

    pub fn shutdown(&mut self) {
        self.rpc_producer.publish(&[], MsgKind::Shutdown);
    }

    fn publish_only<T: Serialize>(&mut self, payload: &T, kind: MsgKind) -> CandleResult<()> {
        let bytes = bincode::serialize(payload).map_err(myelon_to_candle)?;
        if !self.logged_first_request {
            log_info!(
                "Dispatching first Myelon request kind={} bytes={}.",
                kind.as_u8(),
                bytes.len()
            );
            self.logged_first_request = true;
        }
        self.rpc_producer.publish(&bytes, kind);
        Ok(())
    }

    fn publish_and_collect<T: Serialize>(
        &mut self,
        payload: &T,
        kind: MsgKind,
    ) -> CandleResult<Vec<u32>> {
        self.publish_only(payload, kind)?;
        self.collect_outputs()
    }

    fn collect_outputs(&mut self) -> CandleResult<Vec<u32>> {
        let mut first_output: Option<Vec<u32>> = None;

        for consumer in &mut self.response_consumers {
            let (kind, payload) = consumer.recv_message_blocking();
            if !self.logged_first_response {
                log_info!(
                    "Received first Myelon response kind={} bytes={}.",
                    kind,
                    payload.len()
                );
                self.logged_first_response = true;
            }
            if kind == MsgKind::RunResponse.as_u8() {
                let output_ids: Vec<u32> =
                    bincode::deserialize(&payload).map_err(myelon_to_candle)?;
                if let Some(expected) = &first_output {
                    if expected != &output_ids {
                        candle_core::bail!("Myelon runner outputs diverged across ranks");
                    }
                } else {
                    first_output = Some(output_ids);
                }
            } else if kind == MsgKind::Error.as_u8() {
                let error = String::from_utf8_lossy(&payload);
                candle_core::bail!("runner Myelon error: {}", error);
            } else {
                candle_core::bail!("unexpected Myelon response kind {}", kind);
            }
        }

        first_output
            .ok_or_else(|| candle_core::Error::Msg("missing Myelon runner response".to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    use myelon_playground::{frame_flags, publish_framed_payload};

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
}
