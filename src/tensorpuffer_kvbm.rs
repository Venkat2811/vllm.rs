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
//!   The handle frames the layer_data with `tp_node::kv_frame::encode`
//!   (replaces the previous bincode path) and best-effort PUTs through
//!   foyer + S3, keyed by both `seq-{seq_id}` AND a stable
//!   `prefix-{blake3}` content hash so restart-from-S3 can dedupe.
//! - PD consumer: [`load_finished_prefill`] / [`load_by_prefix_hash`]
//!   are intended for the decode side to short-circuit a network transfer
//!   when the same KV is already resident locally. Wiring of the actual
//!   GPU-side replay path is deferred — the keys are present and the
//!   data round-trips with byte fidelity.
//!
//! # Failure mode
//!
//! All public entry points are best-effort: any failure to reach the cache
//! is logged with `tracing::warn` and the engine proceeds as if the
//! tensorpuffer backend were absent.

use std::sync::Arc;

use bytes::Bytes;
use once_cell::sync::OnceCell;
use parking_lot::RwLock;

use tp_node::embed::{EmbedConfig, GetOutcome, HitTier, TensorpufferKvStore};
use tp_node::embed_metrics::metrics;
use tp_node::foyer_cache::FoyerCacheConfig;
use tp_node::kv_frame;
use tp_store::wal_store::{S3ObjectStore, S3ObjectStoreConfig};

#[cfg(feature = "tensorpuffer-remote")]
use tp_puffer_shm::{RemoteGetOutcome, RemoteHitTier, RemoteKvStoreClient};

const DEFAULT_FOYER_DIR: &str = "/tmp/tpuf-foyer";
const DEFAULT_S3_PREFIX: &str = "kv/vllm-rs";

/// Internal dispatch over the active KV backend.
///
/// `Embedded` is the M0 default — `TensorpufferKvStore` lives in this
/// process. `Remote` is M1 — calls hop through a `tp-puffer-shm-daemon`
/// over the SHM ring. The rest of `KvbmHandle` is identical for both.
enum Backend {
    Embedded(Arc<RwLock<TensorpufferKvStore<S3ObjectStore>>>),
    #[cfg(feature = "tensorpuffer-remote")]
    Remote(Arc<RemoteKvStoreClient>),
}

/// Backend-agnostic GET result. Mirrors `tp_node::embed::GetOutcome` but
/// owned by the local crate so both backends can produce it.
enum BackendGetOutcome {
    Hit { tier: HitTier, payload: Bytes },
    Miss,
}

impl Backend {
    /// Static label for metrics / logs. Stable across the handle's
    /// lifetime; "embedded" or "remote".
    fn kind(&self) -> &'static str {
        match self {
            Backend::Embedded(_) => "embedded",
            #[cfg(feature = "tensorpuffer-remote")]
            Backend::Remote(_) => "remote",
        }
    }

    /// True when the backend is in a usable state.
    ///
    /// `Embedded` is always alive for the life of this process — the
    /// foyer + S3 plumbing doesn't cross any process boundary, so the
    /// only way to lose it is to drop the handle entirely.
    ///
    /// `Remote` returns `false` once the client has timed out and
    /// transitioned to dead state. The engine should drop this handle
    /// and rebuild a fresh one (`tensorpuffer_kvbm::init_from_env` after
    /// `reset_for_test()`-style teardown, OR by treating the handle as
    /// disposable per session) when this returns `false`. Today there
    /// is no transparent reconnect; that's M1.2.
    fn is_alive(&self) -> bool {
        match self {
            Backend::Embedded(_) => true,
            #[cfg(feature = "tensorpuffer-remote")]
            Backend::Remote(client) => !client.is_dead(),
        }
    }

    fn put_kv(&self, namespace: &str, key: &str, payload: Bytes) -> Result<(), String> {
        match self {
            Backend::Embedded(store) => {
                let store = store.read();
                store
                    .put_kv(namespace, key, payload)
                    .map_err(|err| format!("{err}"))
            }
            #[cfg(feature = "tensorpuffer-remote")]
            Backend::Remote(client) => {
                client
                    .put_kv(namespace, key, payload)
                    .map_err(|err| format!("{err}"))
            }
        }
    }

    fn get_kv(&self, namespace: &str, key: &str) -> Result<BackendGetOutcome, String> {
        match self {
            Backend::Embedded(store) => {
                let store = store.read();
                match store.get_kv(namespace, key) {
                    Ok(GetOutcome::Hit { tier, payload }) => {
                        Ok(BackendGetOutcome::Hit { tier, payload })
                    }
                    Ok(GetOutcome::Miss) => Ok(BackendGetOutcome::Miss),
                    Err(err) => Err(format!("{err}")),
                }
            }
            #[cfg(feature = "tensorpuffer-remote")]
            Backend::Remote(client) => match client.get_kv(namespace, key) {
                Ok(RemoteGetOutcome::Hit { tier, payload }) => {
                    let tier = match tier {
                        RemoteHitTier::Foyer => HitTier::Foyer,
                        RemoteHitTier::ObjectStore => HitTier::ObjectStore,
                    };
                    Ok(BackendGetOutcome::Hit { tier, payload })
                }
                Ok(RemoteGetOutcome::Miss) => Ok(BackendGetOutcome::Miss),
                Err(err) => Err(format!("{err}")),
            },
        }
    }

    fn restore_from_s3(&self, namespace: &str) -> Result<usize, String> {
        match self {
            Backend::Embedded(store) => {
                let store = store.read();
                store
                    .restore_from_s3(namespace)
                    .map_err(|err| format!("{err}"))
            }
            #[cfg(feature = "tensorpuffer-remote")]
            Backend::Remote(client) => {
                client
                    .restore_from_s3(namespace)
                    .map_err(|err| format!("{err}"))
            }
        }
    }
}

/// Decoded prefill payload. Mirrors the data carried by
/// `crate::transfer::FinishedPrefillData::RemoteTcp` so the decode side
/// can synthesize an equivalent message after a restart.
#[derive(Debug, Clone)]
pub struct StashedPrefill {
    pub seq_id: u64,
    pub first_token: u32,
    pub layer_data: Vec<(Vec<u8>, Vec<u8>)>,
    pub num_blocks: u32,
    pub num_cached_tokens: u32,
}

/// Compute the stable content hash of a prefill prefix. Two requests with
/// the same `(model_id, token_ids)` produce the same hash regardless of
/// when they ran.
#[must_use]
pub fn content_hash_for_prefix(model_id: &str, token_ids: &[u32]) -> String {
    let mut hasher = blake3::Hasher::new();
    hasher.update(b"tpuf-kvbm-v1\0");
    hasher.update(model_id.as_bytes());
    hasher.update(b"\0");
    let n = u32::try_from(token_ids.len()).unwrap_or(u32::MAX);
    hasher.update(&n.to_le_bytes());
    // Tokens are u32; copy into a tightly-packed byte buffer.
    let mut buf = Vec::with_capacity(token_ids.len() * 4);
    for tok in token_ids {
        buf.extend_from_slice(&tok.to_le_bytes());
    }
    hasher.update(&buf);
    hasher.finalize().to_hex().to_string()
}

/// Shared handle to the tensorpuffer KV store. Created once at engine
/// startup; cheap to clone (Arc).
#[derive(Clone)]
pub struct KvbmHandle {
    inner: Arc<Backend>,
    namespace: String,
}

static GLOBAL: OnceCell<Option<KvbmHandle>> = OnceCell::new();

pub fn handle() -> Option<KvbmHandle> {
    GLOBAL.get().and_then(|opt| opt.clone())
}

/// Initialize the global handle from environment variables.
///
/// Required: TPUF_S3_ENDPOINT, TPUF_BUCKET, TPUF_S3_ACCESS_KEY,
/// TPUF_S3_SECRET_KEY.
///
/// Optional: TPUF_KVBM_ENABLE, TPUF_KVBM_NAMESPACE, TPUF_FOYER_*,
/// TPUF_KVBM_RESTORE_ON_START, TPUF_KVBM_S3_PREFIX.
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

    // foyer + rust-s3 each spin up tokio runtimes and call block_on
    // internally; if we initialize them from inside the engine's
    // #[tokio::main] runtime we panic with "Cannot start a runtime from
    // within a runtime." Run the entire init off-runtime.
    let outcome = std::thread::Builder::new()
        .name("tpuf-kvbm-init".to_string())
        .spawn(try_init)
        .and_then(|h| h.join().map_err(|_| std::io::Error::other("kvbm init thread panicked")));

    match outcome {
        Ok(Ok(handle)) => {
            let _ = GLOBAL.set(Some(handle.clone()));
            Some(handle)
        }
        Ok(Err(err)) => {
            tracing::warn!(target: "tensorpuffer", "KVBM init failed; running without tensorpuffer: {err}");
            let _ = GLOBAL.set(None);
            None
        }
        Err(err) => {
            tracing::warn!(target: "tensorpuffer", "KVBM init thread spawn failed: {err}");
            let _ = GLOBAL.set(None);
            None
        }
    }
}

fn try_init() -> Result<KvbmHandle, String> {
    let namespace = std::env::var("TPUF_KVBM_NAMESPACE")
        .unwrap_or_else(|_| "default".to_string());

    let backend = build_backend()?;
    let handle = KvbmHandle {
        inner: Arc::new(backend),
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

fn build_backend() -> Result<Backend, String> {
    // Remote backend (M1): TPUF_KVBM_REMOTE_PREFIX selects a co-located
    // tp-puffer-shm-daemon. Only enabled when the engine was built with
    // `--features tensorpuffer-remote`.
    #[cfg(feature = "tensorpuffer-remote")]
    if let Ok(prefix) = std::env::var("TPUF_KVBM_REMOTE_PREFIX") {
        if !prefix.is_empty() {
            tracing::info!(
                target: "tensorpuffer",
                "KVBM using remote daemon (prefix={prefix})"
            );
            let client = RemoteKvStoreClient::connect(&prefix)
                .map_err(|err| format!("RemoteKvStoreClient::connect({prefix}): {err}"))?;
            return Ok(Backend::Remote(Arc::new(client)));
        }
    }

    // Embedded backend (M0): TensorpufferKvStore lives in this process.
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

    let cfg = EmbedConfig {
        s3_prefix,
        foyer,
        write_through_s3: true,
    };

    let store = TensorpufferKvStore::new(cfg, s3_store)
        .map_err(|err| format!("TensorpufferKvStore::new: {err}"))?;
    tracing::info!(target: "tensorpuffer", "KVBM using embedded backend");
    Ok(Backend::Embedded(Arc::new(RwLock::new(store))))
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

fn seq_key(seq_id: u64) -> String {
    format!("seq-{seq_id:016x}")
}

fn prefix_key(content_hash_hex: &str) -> String {
    format!("prefix-{content_hash_hex}")
}

fn run_off_runtime<R, F>(f: F) -> Option<R>
where
    R: Send + 'static,
    F: Send + 'static + FnOnce() -> R,
{
    std::thread::Builder::new()
        .name("tpuf-kvbm-call".to_string())
        .spawn(f)
        .ok()
        .and_then(|h| h.join().ok())
}

impl KvbmHandle {
    /// Stash a finished prefill payload through both tiers under both a
    /// per-seq key and a stable content-hash key.
    pub fn stash(&self, payload: &StashedPrefill, content_hash_hex: Option<&str>) -> bool {
        // Encode once with kv_frame (replaces bincode).
        let encoded = kv_frame::encode(
            payload.seq_id,
            payload.first_token,
            payload.num_blocks,
            payload.num_cached_tokens,
            &payload.layer_data,
        );
        let bytes = Bytes::from(encoded);
        let backend = self.inner.clone();
        let namespace = self.namespace.clone();
        let seq_id = payload.seq_id;
        let seq_k = seq_key(seq_id);
        let prefix_k = content_hash_hex.map(prefix_key);

        run_off_runtime(move || {
            let mut ok = match backend.put_kv(&namespace, &seq_k, bytes.clone()) {
                Ok(()) => true,
                Err(err) => {
                    tracing::warn!(
                        target: "tensorpuffer",
                        "stash put_kv failed for seq {seq_id}: {err}"
                    );
                    false
                }
            };
            if let Some(prefix_k) = prefix_k {
                if let Err(err) = backend.put_kv(&namespace, &prefix_k, bytes.clone()) {
                    tracing::warn!(
                        target: "tensorpuffer",
                        "stash put_kv (prefix) failed for seq {seq_id}: {err}"
                    );
                    ok = false;
                }
            }
            ok
        })
        .unwrap_or(false)
    }

    /// Best-effort load by seq_id (engine-internal identifier).
    pub fn load_by_seq_id(&self, seq_id: u64) -> Option<StashedPrefill> {
        self.load_by_key(seq_key(seq_id))
    }

    /// Best-effort load by content hash (stable across runs).
    pub fn load_by_prefix_hash(&self, content_hash_hex: &str) -> Option<StashedPrefill> {
        self.load_by_key(prefix_key(content_hash_hex))
    }

    fn load_by_key(&self, key: String) -> Option<StashedPrefill> {
        let backend = self.inner.clone();
        let namespace = self.namespace.clone();
        let bytes = run_off_runtime(move || match backend.get_kv(&namespace, &key) {
            Ok(BackendGetOutcome::Hit { tier, payload }) => {
                let tier_label = match tier {
                    HitTier::Foyer => "foyer",
                    HitTier::ObjectStore => "s3",
                };
                tracing::debug!(
                    target: "tensorpuffer",
                    "load hit for {key} from {tier_label} ({} bytes)",
                    payload.len()
                );
                Some(payload)
            }
            Ok(BackendGetOutcome::Miss) => None,
            Err(err) => {
                tracing::warn!(
                    target: "tensorpuffer",
                    "load get_kv failed for {key}: {err}"
                );
                None
            }
        })
        .flatten()?;

        let view = match kv_frame::decode_owned(&bytes) {
            Ok(v) => v,
            Err(err) => {
                tracing::warn!(
                    target: "tensorpuffer",
                    "load kv_frame::decode_owned failed: {err}"
                );
                return None;
            }
        };
        let (seq_id, _num_layers, num_blocks, first_token, num_cached_tokens, layer_data) = view;
        Some(StashedPrefill {
            seq_id,
            first_token,
            layer_data,
            num_blocks,
            num_cached_tokens,
        })
    }

    pub fn restore_from_s3(&self) -> Result<usize, String> {
        let backend = self.inner.clone();
        let namespace = self.namespace.clone();
        run_off_runtime(move || backend.restore_from_s3(&namespace))
            .unwrap_or_else(|| Err("kvbm restore thread panicked".to_string()))
    }

    /// Static label for the active backend: `"embedded"` (M0) or
    /// `"remote"` (M1). Useful for metrics labels and log context.
    #[must_use]
    pub fn backend_kind(&self) -> &'static str {
        self.inner.kind()
    }

    /// True when the backend is currently usable.
    ///
    /// For `Embedded` this is always `true` — losing it means the whole
    /// process is gone.
    ///
    /// For `Remote` this returns `false` once the client has observed a
    /// per-call timeout and transitioned to dead state. From that point
    /// every call returns `BackendUnavailable` immediately. There is no
    /// transparent reconnect today; the engine should treat the handle
    /// as terminal and degrade to running without puffer (or drop and
    /// rebuild on next request boundary).
    ///
    /// # Recovery pattern
    ///
    /// ```ignore
    /// if let Some(h) = tensorpuffer_kvbm::handle() {
    ///     if !h.is_alive() {
    ///         tracing::warn!("puffer backend dead — rebuilding");
    ///         // Drop the global handle and rebuild from env.
    ///         // (Currently requires test-only reset; production code
    ///         // typically just degrades to no-puffer for the rest of
    ///         // this engine session.)
    ///     }
    /// }
    /// ```
    #[must_use]
    pub fn is_alive(&self) -> bool {
        self.inner.is_alive()
    }
}

/// Convenience entry point used by `transfer/mod.rs`.
pub fn stash_finished_prefill(
    seq_id: u64,
    first_token: u32,
    layer_data: &[(Vec<u8>, Vec<u8>)],
    num_blocks: u32,
    num_cached_tokens: u32,
    content_hash_hex: Option<&str>,
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
    handle.stash(&payload, content_hash_hex)
}

pub fn load_finished_prefill(seq_id: u64) -> Option<StashedPrefill> {
    handle()?.load_by_seq_id(seq_id)
}

pub fn load_finished_prefill_by_prefix(content_hash_hex: &str) -> Option<StashedPrefill> {
    handle()?.load_by_prefix_hash(content_hash_hex)
}

/// `(backend_kind, is_alive)` for the active global handle, or
/// `(None, _)` if puffer is disabled. Cheap — no IPC.
#[must_use]
pub fn backend_health() -> (Option<&'static str>, bool) {
    match handle() {
        Some(h) => (Some(h.backend_kind()), h.is_alive()),
        None => (None, false),
    }
}

/// Render the process-global metrics as one JSON object per op.
#[must_use]
pub fn metrics_report() -> String {
    metrics().to_json_lines()
}

/// Spawn a background thread that periodically logs the metrics report
/// (every `period_ms`). Idempotent — only the first call wins.
pub fn start_metrics_emitter(period_ms: u64) {
    use std::sync::atomic::{AtomicBool, Ordering};
    static STARTED: AtomicBool = AtomicBool::new(false);
    if STARTED.swap(true, Ordering::SeqCst) {
        return;
    }
    let period = std::time::Duration::from_millis(period_ms.max(100));
    std::thread::Builder::new()
        .name("tpuf-metrics-emitter".to_string())
        .spawn(move || loop {
            std::thread::sleep(period);
            let report = metrics().to_json_lines();
            if !report.trim().is_empty() {
                for line in report.lines() {
                    println!("[MyelonInstr] {line}");
                }
            }
        })
        .ok();
}

/// Bytes encoded for a given layer_data, exposed for callers that want
/// to size buffers without actually allocating.
#[must_use]
pub fn encoded_size(layers: &[(Vec<u8>, Vec<u8>)]) -> usize {
    kv_frame::encoded_size(layers)
}
