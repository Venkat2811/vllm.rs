//! Bidirectional Myelon-backed transport for PD KV-cache messages.
//!
//! Two named SHM rings per (rank, role) pair:
//!   - `vllm-rs-pd-c2s-rank{N}` : client→server  (server consumes, client produces)
//!   - `vllm-rs-pd-s2c-rank{N}` : server→client  (server produces, client consumes)
//!
//! `connect()` returns a `(MyelonReader, MyelonWriter)` pair that the
//! `Communicator` stores under its existing reader/writer locks. The reader and
//! writer halves are independent — the Myelon producer and consumer rings do not
//! share state, so no Arc/Mutex is needed between them.
//!
//! Each half implements `Read`/`Write` so the existing length-prefix-then-bincode
//! framing in `comm.rs` works unchanged. One logical bincode message becomes one
//! Myelon `publish` (which fragments into 64KB frames automatically and is
//! reassembled by the consumer's `recv_message_blocking_owned`).

use crate::transfer::PdRole;
use anyhow::{Context, Result};
use myelon_playground::{
    transport::{FramedTransportConsumer, FramedTransportProducer, MyelonWaitStrategy},
    AlignedFixedFrame,
};
use std::io::{Read, Write};
use std::time::{Duration, Instant};

/// Per-frame data capacity. 64KB matches the runner-IPC frame size; large messages
/// (e.g. the ~58MB TransferKvCache payload) get fragmented automatically.
const KV_FRAME_DATA_BYTES: usize = 64 * 1024 - 12;

/// Ring depth (in frames). With 64KB data per frame, depth 1024 = 64MB ring capacity —
/// enough for one in-flight 58MB message without blocking the producer.
const KV_RING_DEPTH: usize = 1024;

const ATTACH_RETRY_INTERVAL: Duration = Duration::from_millis(100);
const ATTACH_TIMEOUT: Duration = Duration::from_secs(120);

pub type KvFrame = AlignedFixedFrame<KV_FRAME_DATA_BYTES>;

fn c2s_ring_name(rank: usize) -> String {
    format!("vllm-rs-pd-c2s-rank{rank}")
}

fn s2c_ring_name(rank: usize) -> String {
    format!("vllm-rs-pd-s2c-rank{rank}")
}

pub struct MyelonReader {
    rx: FramedTransportConsumer<KvFrame>,
    rx_buf: Vec<u8>,
    rx_pos: usize,
}

pub struct MyelonWriter {
    tx: FramedTransportProducer<KvFrame>,
    tx_buf: Vec<u8>,
}

/// Establish the bidirectional channel for the given role + rank.
///
/// Each side creates its outgoing ring first, then attaches to the peer's
/// outgoing ring as a consumer (with retry until the peer has created it).
/// Order-independent: server and client may start in any order.
pub fn connect(role: &PdRole, rank: usize) -> Result<(MyelonReader, MyelonWriter)> {
    let (tx_name, rx_name) = match role {
        PdRole::Server => (s2c_ring_name(rank), c2s_ring_name(rank)),
        PdRole::Client => (c2s_ring_name(rank), s2c_ring_name(rank)),
    };

    let tx = FramedTransportProducer::<KvFrame>::create(&tx_name, KV_RING_DEPTH)
        .with_context(|| format!("failed to create pd ring '{tx_name}'"))?;

    let rx = attach_with_retry(&rx_name, KV_RING_DEPTH)?;

    Ok((
        MyelonReader {
            rx,
            rx_buf: Vec::new(),
            rx_pos: 0,
        },
        MyelonWriter {
            tx,
            tx_buf: Vec::new(),
        },
    ))
}

fn attach_with_retry(
    name: &str,
    depth: usize,
) -> Result<FramedTransportConsumer<KvFrame>> {
    let started = Instant::now();
    loop {
        match FramedTransportConsumer::<KvFrame>::attach(
            name,
            depth,
            MyelonWaitStrategy::Block,
        ) {
            Ok(consumer) => return Ok(consumer),
            Err(_) if started.elapsed() < ATTACH_TIMEOUT => {
                std::thread::sleep(ATTACH_RETRY_INTERVAL);
                continue;
            }
            Err(e) => {
                return Err(anyhow::anyhow!(
                    "timed out attaching to pd ring '{name}' after {:?}: {e:?}",
                    ATTACH_TIMEOUT
                ));
            }
        }
    }
}

impl Read for MyelonReader {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        if self.rx_pos >= self.rx_buf.len() {
            // Fetch the next message from the consumer ring (blocks until available).
            let (_kind, payload) = self.rx.recv_message_blocking_owned();
            self.rx_buf = payload;
            self.rx_pos = 0;
        }
        let available = self.rx_buf.len() - self.rx_pos;
        let n = available.min(buf.len());
        buf[..n].copy_from_slice(&self.rx_buf[self.rx_pos..self.rx_pos + n]);
        self.rx_pos += n;
        Ok(n)
    }
}

// MyelonReader is read-only; provide a no-op Write so it fits the CommStream
// enum which expects Read + Write on each half.
impl Write for MyelonReader {
    fn write(&mut self, _buf: &[u8]) -> std::io::Result<usize> {
        Err(std::io::Error::new(
            std::io::ErrorKind::Unsupported,
            "MyelonReader does not support Write",
        ))
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

impl Write for MyelonWriter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        self.tx_buf.extend_from_slice(buf);
        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        if self.tx_buf.is_empty() {
            return Ok(());
        }
        self.tx.publish(&self.tx_buf, 0u8);
        self.tx_buf.clear();
        Ok(())
    }
}

// MyelonWriter is write-only; provide a no-op Read for symmetry.
impl Read for MyelonWriter {
    fn read(&mut self, _buf: &mut [u8]) -> std::io::Result<usize> {
        Err(std::io::Error::new(
            std::io::ErrorKind::Unsupported,
            "MyelonWriter does not support Read",
        ))
    }
}
