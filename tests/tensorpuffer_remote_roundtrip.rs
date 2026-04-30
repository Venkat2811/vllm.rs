//! End-to-end smoke for the M1 (remote daemon) backend.
//!
//! Spawns a `tp-puffer-shm-daemon` subprocess, builds a `KvbmHandle`
//! pointed at it via `TPUF_KVBM_REMOTE_PREFIX`, stashes a fake prefill,
//! and loads it back. Proves the engine code calls the same `KvbmHandle`
//! methods regardless of M0/M1, and that the M1 wiring round-trips bytes
//! through the SHM ring + foyer + S3 stack with byte fidelity.
//!
//! Skips when MinIO env vars are missing OR the daemon binary cannot be
//! found.
//!
//! Run with:
//!   TPUF_S3_ENDPOINT=http://localhost:9100 TPUF_S3_BUCKET=tpuf-vllm-rs-m1 \
//!   TPUF_S3_ACCESS_KEY=minioadmin TPUF_S3_SECRET_KEY=minioadmin \
//!   TPUF_S3_REGION=us-east-1 TPUF_S3_FORCE_PATH_STYLE=1 \
//!   cargo test --test tensorpuffer_remote_roundtrip \
//!     --features metal,tensorpuffer-remote -- --nocapture

#![cfg(feature = "tensorpuffer-remote")]

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::SystemTime;

use vllm_rs::tensorpuffer_kvbm;

fn unique_prefix() -> String {
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let nanos = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let s = format!("{nanos:x}{seq:x}");
    let n = s.len();
    format!("v{}", &s[n.saturating_sub(6)..])
}

/// Walk up from `current_exe()` looking for the daemon binary built by
/// the workspace. Falls back to TPUF_PUFFER_SHM_DAEMON_BIN env var.
fn find_daemon_bin() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("TPUF_PUFFER_SHM_DAEMON_BIN") {
        let p = PathBuf::from(p);
        if p.is_file() {
            return Some(p);
        }
    }
    let exe = std::env::current_exe().ok()?;
    let mut dir = exe.clone();
    while let Some(parent) = dir.parent() {
        // Try sibling release/debug builds in the same target/.
        for variant in ["release", "debug"] {
            let cand = parent.join(format!("../{variant}/tp-puffer-shm-daemon"));
            if cand.is_file() {
                return Some(cand);
            }
        }
        // Also search rooted at the workspace neighbor.
        let cand = parent.join("../tensorpuffer/target/release/tp-puffer-shm-daemon");
        if cand.is_file() {
            return Some(cand);
        }
        dir = parent.to_path_buf();
    }
    None
}

struct DaemonGuard {
    child: Option<Child>,
}

impl Drop for DaemonGuard {
    fn drop(&mut self) {
        if let Some(mut c) = self.child.take() {
            let _ = c.kill();
            let _ = c.wait();
        }
    }
}

fn s3_env_ok() -> bool {
    ["TPUF_S3_ENDPOINT", "TPUF_S3_BUCKET", "TPUF_S3_ACCESS_KEY", "TPUF_S3_SECRET_KEY"]
        .iter()
        .all(|k| std::env::var(k).is_ok())
}

fn spawn_daemon(prefix: &str) -> Option<DaemonGuard> {
    if !s3_env_ok() {
        eprintln!("skipping: TPUF_S3_* not set");
        return None;
    }
    let bin = find_daemon_bin()?;
    let child = Command::new(&bin)
        .arg("--prefix")
        .arg(prefix)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;
    Some(DaemonGuard { child: Some(child) })
}

#[test]
fn m1_kvbm_stash_then_load_round_trips() {
    let prefix = unique_prefix();
    let Some(_daemon) = spawn_daemon(&prefix) else {
        return;
    };

    // Configure the M1 client path. Setting TPUF_KVBM_REMOTE_PREFIX is
    // what flips the backend to Remote.
    std::env::set_var("TPUF_KVBM_REMOTE_PREFIX", &prefix);
    std::env::set_var("TPUF_KVBM_ENABLE", "1");
    std::env::set_var("TPUF_KVBM_NAMESPACE", "vllm-rs-m1-test");
    std::env::set_var("TPUF_KVBM_RESTORE_ON_START", "0");

    let Some(handle) = tensorpuffer_kvbm::init_from_env() else {
        panic!("init_from_env returned None — daemon connect failed?");
    };

    // Verify backend health probes work.
    assert_eq!(handle.backend_kind(), "remote");
    assert!(handle.is_alive(), "remote backend should be alive after connect");
    let (kind, alive) = tensorpuffer_kvbm::backend_health();
    assert_eq!(kind, Some("remote"));
    assert!(alive);

    // Build a minimally valid StashedPrefill payload. The kv_frame
    // codec doesn't care about token semantics; it just needs the layer
    // bytes to round-trip.
    let layer_data: Vec<(Vec<u8>, Vec<u8>)> = (0..4)
        .map(|i| {
            let k = vec![i as u8; 1024];
            let v = vec![(i + 1) as u8; 1024];
            (k, v)
        })
        .collect();
    let payload = tensorpuffer_kvbm::StashedPrefill {
        seq_id: 0xDEADBEEF,
        first_token: 0xCAFE,
        layer_data: layer_data.clone(),
        num_blocks: 4,
        num_cached_tokens: 0,
    };

    let content_hash = tensorpuffer_kvbm::content_hash_for_prefix(
        "test-model",
        &[1u32, 2, 3, 4, 5, 6, 7, 8],
    );

    assert!(
        handle.stash(&payload, Some(&content_hash)),
        "stash failed against M1 daemon"
    );

    // Load by seq_id.
    let by_seq = handle
        .load_by_seq_id(0xDEADBEEF)
        .expect("load_by_seq_id returned None");
    assert_eq!(by_seq.seq_id, 0xDEADBEEF);
    assert_eq!(by_seq.first_token, 0xCAFE);
    assert_eq!(by_seq.layer_data, layer_data);
    assert_eq!(by_seq.num_blocks, 4);

    // Load by content hash — proves the prefix-keyed alias path works
    // through the daemon too.
    let by_prefix = handle
        .load_by_prefix_hash(&content_hash)
        .expect("load_by_prefix_hash returned None");
    assert_eq!(by_prefix.seq_id, 0xDEADBEEF);
    assert_eq!(by_prefix.layer_data, layer_data);
}
