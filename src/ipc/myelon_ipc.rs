use anyhow::{Context, Result};
use myelon_playground::transport::{
    FramedTransportConsumer, FramedTransportFrame, FramedTransportProducer,
};
pub use myelon_playground::{
    FrameMeta, MyelonTransportLayout, MyelonWaitStrategy, RunnerMyelonTransportConfig,
};

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
