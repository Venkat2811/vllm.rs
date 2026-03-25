use anyhow::{Context, Result};
use myelon_playground::lock_free::SharedCursor;
use myelon_playground::{
    attach_shared_consumer, build_shared_single_producer, ensure_coordination_cursor,
    publish_framed_payload, recv_framed_message, FrameMeta, SharedConsumer, SharedProducer,
};
pub use myelon_playground::{
    MyelonTransportLayout, MyelonWaitStrategy, RunnerMyelonTransportConfig,
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
    _coordination_cursor: SharedCursor,
    inner: SharedProducer<RpcFrame>,
}

impl RpcBroadcastProducer {
    pub fn create(name: &str, depth: usize) -> Result<Self> {
        let coordination_cursor = ensure_coordination_cursor(name)?;
        let inner = build_shared_single_producer::<RpcFrame>(name, depth)
            .build_producer(RpcFrame::default)
            .with_context(|| format!("failed to create rpc ring '{name}'"))?;
        Ok(Self {
            _coordination_cursor: coordination_cursor,
            inner,
        })
    }

    pub fn publish(&mut self, payload: &[u8], kind: MsgKind) {
        publish_framed_payload(
            payload,
            kind.as_u8(),
            RPC_FRAME_DATA_BYTES,
            |frame| self.inner.publish(|slot| *slot = frame),
            make_rpc_frame,
        );
    }
}

pub struct RpcBroadcastConsumer {
    inner: SharedConsumer<RpcFrame>,
    wait_strategy: MyelonWaitStrategy,
}

impl RpcBroadcastConsumer {
    pub fn attach(name: &str, depth: usize, wait_strategy: MyelonWaitStrategy) -> Result<Self> {
        let inner = attach_shared_consumer::<RpcFrame>(name, depth)
            .build_consumer()
            .with_context(|| format!("failed to attach rpc ring '{name}'"))?;
        Ok(Self {
            inner,
            wait_strategy,
        })
    }

    pub fn recv_message_blocking(&mut self) -> (u8, Vec<u8>) {
        recv_framed_message(
            || match self.wait_strategy {
                MyelonWaitStrategy::BusySpin => self.inner.consume_next(),
                MyelonWaitStrategy::Block => self.inner.consume_next_with_sleep(),
            },
            |frame| FrameMeta {
                len: frame.len as usize,
                kind: frame.kind,
                flags: frame.flags,
                msg_id: frame.msg_id,
                data: &frame.data[..frame.len as usize],
            },
        )
    }
}

pub struct ResponseProducer {
    _coordination_cursor: SharedCursor,
    inner: SharedProducer<ResponseFrame>,
}

impl ResponseProducer {
    pub fn create(name: &str, depth: usize) -> Result<Self> {
        let coordination_cursor = ensure_coordination_cursor(name)?;
        let inner = build_shared_single_producer::<ResponseFrame>(name, depth)
            .build_producer(ResponseFrame::default)
            .with_context(|| format!("failed to create response ring '{name}'"))?;
        Ok(Self {
            _coordination_cursor: coordination_cursor,
            inner,
        })
    }

    pub fn send(&mut self, payload: &[u8], kind: MsgKind) {
        publish_framed_payload(
            payload,
            kind.as_u8(),
            RESPONSE_FRAME_DATA_BYTES,
            |frame| self.inner.publish(|slot| *slot = frame),
            make_response_frame,
        );
    }
}

pub struct ResponseConsumer {
    inner: SharedConsumer<ResponseFrame>,
    wait_strategy: MyelonWaitStrategy,
}

impl ResponseConsumer {
    pub fn attach(name: &str, depth: usize, wait_strategy: MyelonWaitStrategy) -> Result<Self> {
        let inner = attach_shared_consumer::<ResponseFrame>(name, depth)
            .build_consumer()
            .with_context(|| format!("failed to attach response ring '{name}'"))?;
        Ok(Self {
            inner,
            wait_strategy,
        })
    }

    pub fn recv_message_blocking(&mut self) -> (u8, Vec<u8>) {
        recv_framed_message(
            || match self.wait_strategy {
                MyelonWaitStrategy::BusySpin => self.inner.consume_next(),
                MyelonWaitStrategy::Block => self.inner.consume_next_with_sleep(),
            },
            |frame| FrameMeta {
                len: frame.len as usize,
                kind: frame.kind,
                flags: frame.flags,
                msg_id: frame.msg_id,
                data: &frame.data[..frame.len as usize],
            },
        )
    }
}

fn make_rpc_frame(payload: &[u8], kind: u8, msg_id: u32, flags: u8) -> RpcFrame {
    let mut frame = RpcFrame::default();
    frame.len = payload.len() as u32;
    frame.kind = kind;
    frame.flags = flags;
    frame.msg_id = msg_id;
    frame.data[..payload.len()].copy_from_slice(payload);
    frame
}

fn make_response_frame(payload: &[u8], kind: u8, msg_id: u32, flags: u8) -> ResponseFrame {
    let mut frame = ResponseFrame::default();
    frame.len = payload.len() as u32;
    frame.kind = kind;
    frame.flags = flags;
    frame.msg_id = msg_id;
    frame.data[..payload.len()].copy_from_slice(payload);
    frame
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    use myelon_playground::frame_flags;

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
            make_rpc_frame,
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

        assert!(consumer.inner.has_coordination_support());

        drop(producer);
    }

    #[test]
    fn response_consumer_sees_coordination_cursor_while_producer_lives() {
        let ring_name = unique_ring_name("vmyrsp");
        let producer = ResponseProducer::create(&ring_name, 8).unwrap();
        let consumer = ResponseConsumer::attach(&ring_name, 8, MyelonWaitStrategy::Block).unwrap();

        assert!(consumer.inner.has_coordination_support());

        drop(producer);
    }
}
