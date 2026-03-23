use anyhow::{anyhow, bail, Context, Result};
use myelon_playground::{
    attach_shared_consumer, build_shared_single_producer, lock_free::SharedCursor, SharedConsumer,
    SharedProducer,
};
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::sync::atomic::{AtomicU32, Ordering};

const SEGMENT_NAME_LIMIT_MACOS: usize = 31;
const TRANSPORT_PREFIX: &str = "vmy";

pub const RPC_FRAME_HEADER_BYTES: usize = 12;
pub const RESPONSE_FRAME_HEADER_BYTES: usize = 12;
pub const RPC_FRAME_DATA_BYTES: usize = 64 * 1024 - RPC_FRAME_HEADER_BYTES;
pub const RESPONSE_FRAME_DATA_BYTES: usize = 4 * 1024 - RESPONSE_FRAME_HEADER_BYTES;

static NEXT_MESSAGE_ID: AtomicU32 = AtomicU32::new(1);

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

#[derive(Copy, Clone, Debug, PartialEq, Eq, Default, Serialize, Deserialize)]
pub enum MyelonWaitStrategy {
    BusySpin,
    #[default]
    Block,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct MyelonTransportLayout {
    session_tag: String,
    rpc_ring_name: String,
    response_ring_names: Vec<String>,
    rpc_depth: usize,
    response_depth: usize,
}

impl MyelonTransportLayout {
    pub fn for_session(
        session_label: &str,
        runner_count: usize,
        rpc_depth: usize,
        response_depth: usize,
    ) -> Result<Self> {
        if runner_count == 0 {
            bail!("runner_count must be greater than zero");
        }
        if rpc_depth == 0 {
            bail!("rpc_depth must be greater than zero");
        }
        if response_depth == 0 {
            bail!("response_depth must be greater than zero");
        }

        let session_tag = compact_session_tag(session_label);
        let rpc_ring_name = format!("{TRANSPORT_PREFIX}{session_tag}p");
        validate_segment_name(&rpc_ring_name)?;

        let mut response_ring_names = Vec::with_capacity(runner_count);
        for rank in 0..runner_count {
            let response_ring_name = format!("{TRANSPORT_PREFIX}{session_tag}r{rank:x}");
            validate_segment_name(&response_ring_name)?;
            response_ring_names.push(response_ring_name);
        }

        Ok(Self {
            session_tag,
            rpc_ring_name,
            response_ring_names,
            rpc_depth,
            response_depth,
        })
    }

    pub fn session_tag(&self) -> &str {
        &self.session_tag
    }

    pub fn rpc_ring_name(&self) -> &str {
        &self.rpc_ring_name
    }

    pub fn rpc_depth(&self) -> usize {
        self.rpc_depth
    }

    pub fn response_depth(&self) -> usize {
        self.response_depth
    }

    pub fn runner_count(&self) -> usize {
        self.response_ring_names.len()
    }

    pub fn response_ring_name(&self, rank: usize) -> Result<&str> {
        self.response_ring_names
            .get(rank)
            .map(String::as_str)
            .ok_or_else(|| anyhow!("rank {} is out of range for {}", rank, self.runner_count()))
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunnerMyelonTransportConfig {
    pub rpc_ring_name: String,
    pub rpc_depth: usize,
    pub response_ring_name: String,
    pub response_depth: usize,
    pub wait_strategy: MyelonWaitStrategy,
}

impl RunnerMyelonTransportConfig {
    pub fn for_rank(
        layout: &MyelonTransportLayout,
        rank: usize,
        wait_strategy: MyelonWaitStrategy,
    ) -> Result<Self> {
        Ok(Self {
            rpc_ring_name: layout.rpc_ring_name().to_string(),
            rpc_depth: layout.rpc_depth(),
            response_ring_name: layout.response_ring_name(rank)?.to_string(),
            response_depth: layout.response_depth(),
            wait_strategy,
        })
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
        publish_frames(
            payload,
            kind,
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
        recv_message_blocking(
            self.wait_strategy,
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
        publish_frames(
            payload,
            kind,
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
        recv_message_blocking(
            self.wait_strategy,
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

#[derive(Clone, Copy)]
struct FrameMeta<'a> {
    len: usize,
    kind: u8,
    flags: u8,
    msg_id: u32,
    data: &'a [u8],
}

fn coordination_cursor_name(base_name: &str) -> String {
    format!("{base_name}_cr")
}

fn ensure_coordination_cursor(base_name: &str) -> Result<SharedCursor> {
    let cursor_name = coordination_cursor_name(base_name);
    SharedCursor::new_or_attach(&cursor_name, 0)
        .with_context(|| format!("failed to create coordination cursor '{cursor_name}'"))
}

fn recv_message_blocking<F, T, M>(
    _wait_strategy: MyelonWaitStrategy,
    mut next_frame: F,
    mut meta: M,
) -> (u8, Vec<u8>)
where
    F: FnMut() -> (i64, T),
    M: for<'a> FnMut(&'a T) -> FrameMeta<'a>,
{
    let (_, first_frame) = next_frame();
    let first = meta(&first_frame);
    if is_single_frame(first.flags) {
        return (first.kind, first.data.to_vec());
    }

    let mut payload = Vec::with_capacity(first.len.max(1024));
    payload.extend_from_slice(first.data);
    let msg_id = first.msg_id;
    let kind = first.kind;

    if is_last_frame(first.flags) {
        return (kind, payload);
    }

    loop {
        let (_, frame) = next_frame();
        let frame = meta(&frame);
        if frame.msg_id != msg_id {
            continue;
        }
        payload.extend_from_slice(frame.data);
        if is_last_frame(frame.flags) {
            return (kind, payload);
        }
    }
}

fn publish_frames<T, P, W>(
    payload: &[u8],
    kind: MsgKind,
    chunk_size: usize,
    mut write_frame: W,
    mut make_frame: P,
) where
    T: Copy,
    P: FnMut(&[u8], MsgKind, u32, u8) -> T,
    W: FnMut(T),
{
    let msg_id = NEXT_MESSAGE_ID.fetch_add(1, Ordering::Relaxed);
    if payload.is_empty() {
        let frame = make_frame(payload, kind, msg_id, frame_flags(true, true));
        write_frame(frame);
        return;
    }

    for (index, chunk) in payload.chunks(chunk_size).enumerate() {
        let last = (index + 1) * chunk_size >= payload.len();
        let flags = frame_flags(index == 0, last);
        let frame = make_frame(chunk, kind, msg_id, flags);
        write_frame(frame);
    }
}

fn make_rpc_frame(payload: &[u8], kind: MsgKind, msg_id: u32, flags: u8) -> RpcFrame {
    let mut frame = RpcFrame::default();
    frame.len = payload.len() as u32;
    frame.kind = kind.as_u8();
    frame.flags = flags;
    frame.msg_id = msg_id;
    frame.data[..payload.len()].copy_from_slice(payload);
    frame
}

fn make_response_frame(payload: &[u8], kind: MsgKind, msg_id: u32, flags: u8) -> ResponseFrame {
    let mut frame = ResponseFrame::default();
    frame.len = payload.len() as u32;
    frame.kind = kind.as_u8();
    frame.flags = flags;
    frame.msg_id = msg_id;
    frame.data[..payload.len()].copy_from_slice(payload);
    frame
}

fn frame_flags(is_first: bool, is_last: bool) -> u8 {
    let mut flags = 0u8;
    if is_first {
        flags |= 0b01;
    }
    if is_last {
        flags |= 0b10;
    }
    flags
}

fn is_single_frame(flags: u8) -> bool {
    flags & 0b11 == 0b11
}

fn is_last_frame(flags: u8) -> bool {
    flags & 0b10 != 0
}

fn compact_session_tag(session_label: &str) -> String {
    let filtered = session_label
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric())
        .map(|ch| ch.to_ascii_lowercase())
        .collect::<String>();

    if filtered.len() >= 8 {
        return filtered[filtered.len() - 8..].to_string();
    }

    let mut hasher = DefaultHasher::new();
    session_label.hash(&mut hasher);
    format!("{:08x}", hasher.finish() as u32)
}

fn validate_segment_name(name: &str) -> Result<()> {
    if name.is_empty() {
        bail!("segment name must not be empty");
    }
    if name.len() > SEGMENT_NAME_LIMIT_MACOS {
        bail!(
            "segment name '{name}' exceeds conservative macOS limit {}",
            SEGMENT_NAME_LIMIT_MACOS
        );
    }
    if !name.chars().all(|ch| ch.is_ascii_alphanumeric()) {
        bail!("segment name '{name}' must be ASCII alphanumeric only");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering as AtomicOrdering};
    use std::time::{SystemTime, UNIX_EPOCH};

    static UNIQUE_SUFFIX: AtomicU64 = AtomicU64::new(0);

    #[test]
    fn compact_session_tag_is_stable_and_short() {
        let tag = compact_session_tag("4c2f1cb7-50fa-4edf-bd83-very-long-session-name");
        assert_eq!(tag.len(), 8);
        assert!(tag.chars().all(|ch| ch.is_ascii_alphanumeric()));
    }

    #[test]
    fn transport_layout_uses_portable_names() {
        let layout = MyelonTransportLayout::for_session(
            "4c2f1cb7-50fa-4edf-bd83-very-long-session-name",
            3,
            1024,
            256,
        )
        .unwrap();

        assert_eq!(layout.runner_count(), 3);
        assert!(layout.rpc_ring_name().len() <= SEGMENT_NAME_LIMIT_MACOS);
        assert!(layout.response_ring_name(0).unwrap().len() <= SEGMENT_NAME_LIMIT_MACOS);
        assert!(layout.response_ring_name(1).unwrap().starts_with("vmy"));
        assert_eq!(layout.rpc_depth(), 1024);
        assert_eq!(layout.response_depth(), 256);
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

        publish_frames(
            &payload,
            MsgKind::RunDecode,
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
    fn ensure_coordination_cursor_is_idempotent() {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .subsec_nanos() as u64;
        let suffix = UNIQUE_SUFFIX.fetch_add(1, AtomicOrdering::Relaxed);
        let base_name = format!("vmyt{:08x}", (nanos ^ suffix) as u32);

        let first = ensure_coordination_cursor(&base_name).unwrap();
        let second = ensure_coordination_cursor(&base_name).unwrap();

        assert_eq!(
            coordination_cursor_name(&base_name),
            format!("{base_name}_cr")
        );
        assert_eq!(first.load(std::sync::atomic::Ordering::Acquire), 0);
        assert_eq!(second.load(std::sync::atomic::Ordering::Acquire), 0);
    }
}
