//! Tensorpuffer-backed KV cache buffer manager for vllm.rs.
//!
//! Wires the embeddable [`tp_node::embed::TensorpufferKvStore`] into the
//! prefill/transfer hot path so every PD prefill (and, eventually, every
//! single-engine prefill) is also stashed in foyer + S3.
//!
//! # Design (mirrors NVIDIA Dynamo's KVBM connector pattern)
//!
//! - Engine startup: [`init_from_env`] reads `TPUF_*` env vars and opens a
//!   single global [`KvbmHandle`]. Optionally calls
//!   [`KvbmHandle::restore_from_s3`] to rehydrate foyer from MinIO/S3.
//! - PD producer: [`stash_finished_prefill`] is called from
//!   `transfer/mod.rs` right after `FinishedPrefillData` is constructed.
//!   The handle bincode-serializes the payload and best-effort PUTs it
//!   through foyer + S3.
//! - PD consumer: [`load_finished_prefill`] is intended for the decode
//!   side to short-circuit a network transfer when the same KV is already
//!   resident locally (e.g. after a restart). Wiring is deferred.
//!
//! # Failure mode
//!
//! All public entry points are best-effort: any failure to reach the cache
//! is logged with `tracing::warn` and the engine proceeds as if the
//! tensorpuffer backend were absent. There is **no** code path where the
//! engine returns an error to the caller because tensorpuffer is unhappy.

use std::sync::Arc;

use bincode;
use bytes::Bytes;
use once_cell::sync::OnceCell;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};

use tp_node::embed::{EmbedConfig, GetOutcome, HitTier, TensorpufferKvStore};
use tp_node::foyer_cache::FoyerCacheConfig;
use tp_store::wal_store::{S3ObjectStore, S3ObjectStoreConfig};

/// Reuse the same disk root as tp-foyer-kv for symmetry with tensorpuffer
/// tooling.
const DEFAULT_FOYER_DIR: &str = "/tmp/tpuf-foyer";
const DEFAULT_S3_PREFIX: &str = "kv/vllm-rs";

/// Simplified mirror of `crate::transfer::FinishedPrefillData` used for
/// bincode round-trips. Only the bytes-only `RemoteTcp` variant is
/// supported — `LocalIpc` cannot be persisted across processes anyway.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StashedPrefill {
    pub seq_id: usize,
    pub first_token: u32,
    pub layer_data: Vec<(Vec<u8>, Vec<u8>)>,
    pub num_blocks: usize,
    pub num_cached_tokens: usize,
}

/// Shared handle to the tensorpuffer KV store. Created once at engine
/// startup; cheap to clone (Arc + RwLock).
#[derive(Clone)]
pub struct KvbmHandle {
    inner: Arc<RwLock<TensorpufferKvStore<S3ObjectStore>>>,
    namespace: String,
}

static GLOBAL: OnceCell<Option<KvbmHandle>> = OnceCell::new();

/// Look up the global handle. Returns `None` if `init_from_env` was not
/// called or returned `None`.
pub fn handle() -> Option<KvbmHandle> {
    GLOBAL.get().and_then(|opt| opt.clone())
}

/// Initialize the global handle from environment variables. Must be
/// called once at engine startup. Subsequent calls are no-ops and return
/// the previously-installed value.
///
/// Required environment:
///   TPUF_S3_ENDPOINT, TPUF_BUCKET, TPUF_S3_ACCESS_KEY, TPUF_S3_SECRET_KEY
///
/// Optional environment:
///   TPUF_KVBM_ENABLE                (default false; "1" / "true" to enable)
///   TPUF_KVBM_NAMESPACE             (default "default")
///   TPUF_FOYER_RAM_BYTES            (default 1 GiB)
///   TPUF_FOYER_SSD_DIR              (default /tmp/tpuf-foyer)
///   TPUF_FOYER_SSD_BYTES            (default 8 GiB)
///   TPUF_FOYER_BLOCK_SIZE_BYTES     (default 64 MiB)
///   TPUF_KVBM_RESTORE_ON_START      (default "1"; "0" to skip)
pub fn init_from_env() -> Option<KvbmHandle> {
    if let Some(installed) = GLOBAL.get() {
        return installed.clone();
    }

    let enabled = matches!(
        std::env::var("TPUF_KVBM_ENABLE").ok().as_deref(),
        Some("1") | Some("true") | Some("TRUE") | Some("True")
    );
    if !enabled {
        let _ = GLOBAL.set(None);
        return None;
    }

    match try_init() {
        Ok(handle) => {
            let _ = GLOBAL.set(Some(handle.clone()));
            Some(handle)
        }
        Err(err) => {
            tracing::warn!(target: "tensorpuffer", "KVBM init failed; running without tensorpuffer: {err}");
            let _ = GLOBAL.set(None);
            None
        }
    }
}

fn try_init() -> Result<KvbmHandle, String> {
    let s3_cfg = S3ObjectStoreConfig::from_env()
        .map_err(|err| format!("S3 config from env: {err:?}"))?;
    let s3_store = S3ObjectStore::new(s3_cfg)
        .map_err(|err| format!("S3ObjectStore::new: {err:?}"))?;
    s3_store
        .ensure_bucket()
        .map_err(|err| format!("ensure_bucket: {err:?}"))?;

    let foyer = foyer_config_from_env();
    let s3_prefix = std::env::var("TPUF_KVBM_S3_PREFIX")
        .unwrap_or_else(|_| DEFAULT_S3_PREFIX.to_string());
    let namespace = std::env::var("TPUF_KVBM_NAMESPACE")
        .unwrap_or_else(|_| "default".to_string());

    let cfg = EmbedConfig {
        s3_prefix,
        foyer,
        write_through_s3: true,
    };

    let store = TensorpufferKvStore::new(cfg, s3_store)
        .map_err(|err| format!("TensorpufferKvStore::new: {err}"))?;

    let handle = KvbmHandle {
        inner: Arc::new(RwLock::new(store)),
        namespace,
    };

    if env_flag("TPUF_KVBM_RESTORE_ON_START", true) {
        match handle.restore_from_s3() {
            Ok(restored) => {
                tracing::info!(
                    target: "tensorpuffer",
                    "KVBM restored {restored} keys from S3 at startup"
                );
            }
            Err(err) => {
                tracing::warn!(
                    target: "tensorpuffer",
                    "KVBM restore_from_s3 failed (continuing): {err}"
                );
            }
        }
    }

    Ok(handle)
}

fn foyer_config_from_env() -> FoyerCacheConfig {
    let mut cfg = FoyerCacheConfig::default();
    cfg.ssd_dir = std::env::var("TPUF_FOYER_SSD_DIR")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|_| std::path::PathBuf::from(DEFAULT_FOYER_DIR));
    if let Ok(value) = std::env::var("TPUF_FOYER_RAM_BYTES") {
        if let Ok(parsed) = value.parse::<u64>() {
            cfg.ram_bytes = parsed;
        }
    }
    if let Ok(value) = std::env::var("TPUF_FOYER_SSD_BYTES") {
        if let Ok(parsed) = value.parse::<u64>() {
            cfg.ssd_bytes = parsed;
        }
    }
    if let Ok(value) = std::env::var("TPUF_FOYER_BLOCK_SIZE_BYTES") {
        if let Ok(parsed) = value.parse::<usize>() {
            cfg.block_size = parsed;
        }
    }
    if let Ok(value) = std::env::var("TPUF_FOYER_IOURING") {
        cfg.iouring = !(value == "0" || value.eq_ignore_ascii_case("false"));
    }
    cfg
}

fn env_flag(name: &str, default_on: bool) -> bool {
    match std::env::var(name).ok().as_deref() {
        Some("0") | Some("false") | Some("FALSE") | Some("False") => false,
        Some(_) => true,
        None => default_on,
    }
}

fn cache_key(seq_id: usize) -> String {
    format!("seq-{seq_id:016x}")
}

impl KvbmHandle {
    /// Stash a finished prefill payload through both tiers. Returns false
    /// if the put failed; the caller should treat this as a hint, not an
    /// error.
    pub fn stash(&self, payload: &StashedPrefill) -> bool {
        let bytes = match bincode::serialize(payload) {
            Ok(value) => Bytes::from(value),
            Err(err) => {
                tracing::warn!(
                    target: "tensorpuffer",
                    "stash bincode failed for seq {}: {err}", payload.seq_id
                );
                return false;
            }
        };
        let key = cache_key(payload.seq_id);
        let store = self.inner.read();
        match store.put_kv(&self.namespace, &key, bytes) {
            Ok(()) => true,
            Err(err) => {
                tracing::warn!(
                    target: "tensorpuffer",
                    "stash put_kv failed for seq {}: {err}", payload.seq_id
                );
                false
            }
        }
    }

    /// Best-effort load of a previously-stashed prefill payload by seq_id.
    pub fn load(&self, seq_id: usize) -> Option<StashedPrefill> {
        let key = cache_key(seq_id);
        let store = self.inner.read();
        match store.get_kv(&self.namespace, &key) {
            Ok(GetOutcome::Hit { tier, payload }) => {
                let tier_label = match tier {
                    HitTier::Foyer => "foyer",
                    HitTier::ObjectStore => "s3",
                };
                tracing::debug!(
                    target: "tensorpuffer",
                    "load hit for seq {seq_id} from {tier_label} ({} bytes)",
                    payload.len()
                );
                match bincode::deserialize::<StashedPrefill>(&payload) {
                    Ok(value) => Some(value),
                    Err(err) => {
                        tracing::warn!(
                            target: "tensorpuffer",
                            "load bincode failed for seq {seq_id}: {err}"
                        );
                        None
                    }
                }
            }
            Ok(GetOutcome::Miss) => None,
            Err(err) => {
                tracing::warn!(
                    target: "tensorpuffer",
                    "load get_kv failed for seq {seq_id}: {err}"
                );
                None
            }
        }
    }

    /// Restore foyer state from S3 for the configured namespace. Called
    /// once at engine startup when `TPUF_KVBM_RESTORE_ON_START` is set.
    pub fn restore_from_s3(&self) -> Result<usize, String> {
        let store = self.inner.read();
        store
            .restore_from_s3(&self.namespace)
            .map_err(|err| format!("{err}"))
    }
}

/// Convenience entry point used by `transfer/mod.rs`. Mirrors the shape of
/// `FinishedPrefillData` but flattens to `StashedPrefill` to keep the
/// crate boundary clean.
pub fn stash_finished_prefill(
    seq_id: usize,
    first_token: u32,
    layer_data: &[(Vec<u8>, Vec<u8>)],
    num_blocks: usize,
    num_cached_tokens: usize,
) -> bool {
    let Some(handle) = handle() else {
        return false;
    };
    let payload = StashedPrefill {
        seq_id,
        first_token,
        layer_data: layer_data.to_vec(),
        num_blocks,
        num_cached_tokens,
    };
    handle.stash(&payload)
}

/// Convenience entry point for the consumer side. Returns the previously
/// stashed payload, or None if no entry exists / the global handle is
/// uninitialized.
pub fn load_finished_prefill(seq_id: usize) -> Option<StashedPrefill> {
    handle()?.load(seq_id)
}

