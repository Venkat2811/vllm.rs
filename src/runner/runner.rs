use interprocess::local_socket::traits::Stream;
use interprocess::local_socket::Stream as LocalStream;
use interprocess::local_socket::{GenericNamespaced, ToNsName};
use interprocess::TryClone;
use parking_lot::RwLock;
use std::io::Write;
use std::rc::Rc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokenizers::Tokenizer;
use vllm_rs::core::runner::{ModelRunner, Seqs};
#[cfg(feature = "myelon")]
use vllm_rs::ipc::myelon_ipc::{
    MyelonRequest, MyelonResponse, MyelonTransportAccessMode, MyelonTransportBackend,
    ResponseProducer, RpcBroadcastConsumer,
};
#[cfg(all(feature = "myelon", feature = "codec-rkyv"))]
use vllm_rs::ipc::typed_codec::BorrowedTypedMyelonRequest;
use vllm_rs::models::layers::distributed::Comm;
use vllm_rs::models::layers::VarBuilderX;
use vllm_rs::runner::{receive_local, send_local, MessageType};
use vllm_rs::transfer::PdRole;
use vllm_rs::transfer::Transfer;
use vllm_rs::utils::gguf_helper::load_gguf_info_from_files;
use vllm_rs::utils::guidance::build_llg_factory;
use vllm_rs::utils::heartbeat::heartbeat_worker;
use vllm_rs::utils::new_device;
use vllm_rs::utils::progress::{ProgressLike, ProgressReporter, RemoteProgressReporter};

/// Stash a sequence's current KV state (prefill or post-decode) through
/// tensorpuffer. Mirrors the GPU→CPU copy + bytes serialization that
/// `transfer/mod.rs::transfer_kv_cache` performs for PD, but writes to
/// the embedded KV store instead of sending over the PD wire. Keyed by
/// content hash of the CURRENT seq.token_ids — for prefill this is the
/// prompt; for post-decode it's prompt + emitted tokens — so each
/// snapshot lives under its own key and a restart can resume from the
/// deepest matching prefix in foyer/S3.
#[cfg(feature = "tensorpuffer")]
fn stash_seq_kv_local(
    runner: &ModelRunner,
    seq: &vllm_rs::core::sequence::Sequence,
    phase: &'static str,
) {
    use candle_core::DType;
    use std::collections::HashMap;
    use vllm_rs::transfer::{copy_blocks_to_cpu, cpu_tensor_to_bytes};

    if seq.block_table.is_empty() {
        return;
    }

    let server_block_ids = &seq.block_table;
    let mapping: HashMap<usize, usize> = server_block_ids
        .iter()
        .enumerate()
        .map(|(i, &server_id)| (server_id as usize, i))
        .collect();

    let gpu_cache = runner.get_kv_cache();
    if gpu_cache.is_empty() {
        return;
    }
    let dtype = gpu_cache[0].0.dtype();
    let mut layer_data: Vec<(Vec<u8>, Vec<u8>)> = Vec::with_capacity(gpu_cache.len());
    for (k_tensor, v_tensor) in gpu_cache.iter() {
        let k_cpu = match copy_blocks_to_cpu(k_tensor, &mapping, server_block_ids.len()) {
            Ok(t) => t,
            Err(err) => {
                vllm_rs::log_warn!(
                    "[kv stash] copy_blocks_to_cpu k failed for Seq {}: {err}",
                    seq.id
                );
                return;
            }
        };
        let v_cpu = match copy_blocks_to_cpu(v_tensor, &mapping, server_block_ids.len()) {
            Ok(t) => t,
            Err(err) => {
                vllm_rs::log_warn!(
                    "[kv stash] copy_blocks_to_cpu v failed for Seq {}: {err}",
                    seq.id
                );
                return;
            }
        };
        let (k_bytes, v_bytes) = match dtype {
            DType::F16 => (
                match cpu_tensor_to_bytes::<half::f16>(&k_cpu) {
                    Ok(b) => b,
                    Err(_) => return,
                },
                match cpu_tensor_to_bytes::<half::f16>(&v_cpu) {
                    Ok(b) => b,
                    Err(_) => return,
                },
            ),
            DType::BF16 => (
                match cpu_tensor_to_bytes::<half::bf16>(&k_cpu) {
                    Ok(b) => b,
                    Err(_) => return,
                },
                match cpu_tensor_to_bytes::<half::bf16>(&v_cpu) {
                    Ok(b) => b,
                    Err(_) => return,
                },
            ),
            DType::U8 => (
                match cpu_tensor_to_bytes::<u8>(&k_cpu) {
                    Ok(b) => b,
                    Err(_) => return,
                },
                match cpu_tensor_to_bytes::<u8>(&v_cpu) {
                    Ok(b) => b,
                    Err(_) => return,
                },
            ),
            other => {
                vllm_rs::log_warn!(
                    "[kv stash] unsupported dtype {:?} for Seq {}",
                    other,
                    seq.id
                );
                return;
            }
        };
        layer_data.push((k_bytes, v_bytes));
    }
    drop(gpu_cache);

    let prefix_hash =
        vllm_rs::tensorpuffer_kvbm::content_hash_for_prefix("vllm-rs", &seq.token_ids);
    // Record the prefix-cache hit length seen by FUTURE consumers. The
    // stashed bytes contain KV for the full `seq.token_ids.len()`
    // tokens; that's the number a future try-load should set
    // `seq.num_cached_tokens` to so the engine's existing prefix-cache
    // logic skips the prefill compute.
    //
    // (Field is named `num_cached_tokens` for historical PD-disagg
    // reasons. Semantically here it's "tokens-already-prefilled-in-
    // these-blocks".)
    let stashed = vllm_rs::tensorpuffer_kvbm::stash_finished_prefill(
        seq.id as u64,
        seq.last_token,
        &layer_data,
        seq.block_table.len() as u32,
        seq.token_ids.len() as u32,
        Some(&prefix_hash),
    );
    if std::env::var("MYELON_INSTRUMENT").map(|v| v == "1").unwrap_or(false) {
        println!(
            "[MyelonInstr] {}",
            serde_json::json!({
                "scope": "tensorpuffer_kvbm",
                "op": "stash_kv_local",
                "phase": phase,
                "seq_id": seq.id,
                "stashed": stashed,
                "layers": layer_data.len(),
                "blocks": seq.block_table.len(),
                "tokens": seq.token_ids.len(),
                "prefix_hash": prefix_hash,
            })
        );
    }
}

/// Try to import a sequence's KV cache from tensorpuffer BEFORE
/// running prefill. If a stashed prefix matching `seq.token_ids` is
/// found, write the bytes into the runner's GPU KV cache for the
/// seq's already-allocated blocks and bump `seq.num_cached_tokens` so
/// the engine's existing prefix-cache logic skips the cached prefix.
///
/// Returns `true` on import (caller should treat the seq as
/// pre-prefilled) or `false` on miss / mismatch (caller falls through
/// to normal prefill).
///
/// Gated by `TPUF_KVBM_TRY_LOAD=1` so existing benchmarks aren't
/// affected. Mirrors the byte-fidelity primitives the PD-disagg
/// `KVTransferHandle::RemoteTcp` path already uses
/// (`bytes_to_cpu_tensor` → `swap_blocks`).
#[cfg(feature = "tensorpuffer")]
fn try_import_seq_kv_from_puffer(
    runner: &ModelRunner,
    seq: &mut vllm_rs::core::sequence::Sequence,
) -> bool {
    use std::collections::HashMap;
    use vllm_rs::transfer::bytes_to_cpu_tensor;

    if seq.token_ids.is_empty() || seq.block_table.is_empty() {
        return false;
    }

    // 1. Lookup by content hash.
    let prefix_hash = vllm_rs::tensorpuffer_kvbm::content_hash_for_prefix(
        "vllm-rs",
        &seq.token_ids,
    );
    let stashed = match vllm_rs::tensorpuffer_kvbm::load_finished_prefill_by_prefix(
        &prefix_hash,
    ) {
        Some(s) => s,
        None => return false,
    };

    // 2. Shape sanity.
    let gpu_cache = runner.get_kv_cache();
    if gpu_cache.is_empty() {
        return false;
    }
    if stashed.layer_data.len() != gpu_cache.len() {
        vllm_rs::log_warn!(
            "[try-load] layer count mismatch: stashed={} runner={} — falling through",
            stashed.layer_data.len(),
            gpu_cache.len()
        );
        return false;
    }
    let n_blocks = stashed.num_blocks as usize;
    if n_blocks == 0 || seq.block_table.len() < n_blocks {
        return false;
    }

    // 3. Map stashed[i] → seq's i-th allocated block.
    let mapping: HashMap<usize, usize> = (0..n_blocks)
        .map(|i| (i, seq.block_table[i] as usize))
        .collect();

    // 4. Import each layer.
    for (i, (k_bytes, v_bytes)) in stashed.layer_data.iter().enumerate() {
        let (local_k_cache, local_v_cache) = &gpu_cache[i];
        let remote_k = match bytes_to_cpu_tensor(k_bytes, n_blocks, local_k_cache) {
            Ok(t) => t,
            Err(err) => {
                vllm_rs::log_warn!(
                    "[try-load] bytes_to_cpu_tensor (k) failed for seq {}: {err}",
                    seq.id
                );
                return false;
            }
        };
        let remote_v = match bytes_to_cpu_tensor(v_bytes, n_blocks, local_v_cache) {
            Ok(t) => t,
            Err(err) => {
                vllm_rs::log_warn!(
                    "[try-load] bytes_to_cpu_tensor (v) failed for seq {}: {err}",
                    seq.id
                );
                return false;
            }
        };
        if let Err(err) = attention_rs::cache::swap_blocks(&remote_k, local_k_cache, &mapping) {
            vllm_rs::log_warn!("[try-load] swap_blocks (k) failed for seq {}: {err}", seq.id);
            return false;
        }
        if let Err(err) = attention_rs::cache::swap_blocks(&remote_v, local_v_cache, &mapping) {
            vllm_rs::log_warn!("[try-load] swap_blocks (v) failed for seq {}: {err}", seq.id);
            return false;
        }
    }
    drop(gpu_cache);

    // 5. Mark seq as pre-prefilled. The engine's existing prefix-cache
    //    logic respects this and only computes the un-cached suffix.
    //    Cap at `token_ids.len() - 1` so there's always at least one
    //    token left for the engine to prefill — this is what produces
    //    the logits the sampler needs to start decoding. Setting cached
    //    == total causes a "0 tokens to prefill" panic in the runner's
    //    input validator.
    let recorded = stashed.num_cached_tokens as usize;
    let max_cacheable = seq.token_ids.len().saturating_sub(1);
    let cached_tokens = recorded.min(max_cacheable);
    seq.num_cached_tokens = cached_tokens;

    if std::env::var("MYELON_INSTRUMENT").map(|v| v == "1").unwrap_or(false) {
        println!(
            "[MyelonInstr] {}",
            serde_json::json!({
                "scope": "tensorpuffer_kvbm",
                "op": "try_import_kv_local",
                "seq_id": seq.id,
                "imported_blocks": n_blocks,
                "cached_tokens": cached_tokens,
                "tokens": seq.token_ids.len(),
                "prefix_hash": prefix_hash,
            })
        );
    }
    vllm_rs::log_info!(
        "[try-load] seq {} imported {} blocks ({} cached tokens) from puffer",
        seq.id,
        n_blocks,
        cached_tokens
    );

    true
}

/// Returns true if non-PD pre-prefill try-load is enabled. Off by
/// default. Enable with `TPUF_KVBM_TRY_LOAD=1`.
#[cfg(feature = "tensorpuffer")]
fn try_load_enabled() -> bool {
    matches!(
        std::env::var("TPUF_KVBM_TRY_LOAD").ok().as_deref(),
        Some("1") | Some("true") | Some("TRUE") | Some("True")
    )
}

/// Returns true if non-PD decode-side stashing is enabled. Off by
/// default (prefill stash is the common case; decode stashing creates
/// one S3 PUT per token-step which is a lot for some workloads).
/// Enable with `TPUF_KVBM_STASH_DECODE=1`.
#[cfg(feature = "tensorpuffer")]
fn decode_stash_enabled() -> bool {
    matches!(
        std::env::var("TPUF_KVBM_STASH_DECODE").ok().as_deref(),
        Some("1") | Some("true") | Some("TRUE") | Some("True")
    )
}

/// Per-seq token-id cache populated during prefill so the decode-side
/// stash can compute a content hash. RunDecode messages only carry
/// `DecodeSequence` (id, last_token, block_tables) — they intentionally
/// don't ship the full token list to keep the wire small. We rebuild
/// the running list here by snapshotting `seq.token_ids` on prefill
/// and appending `last_token` on each subsequent decode.
#[cfg(feature = "tensorpuffer")]
static RUNNER_SEQ_TOKENS: std::sync::OnceLock<
    std::sync::Mutex<std::collections::HashMap<usize, Vec<u32>>>,
> = std::sync::OnceLock::new();

#[cfg(feature = "tensorpuffer")]
fn runner_seq_tokens() -> &'static std::sync::Mutex<
    std::collections::HashMap<usize, Vec<u32>>,
> {
    RUNNER_SEQ_TOKENS.get_or_init(|| std::sync::Mutex::new(std::collections::HashMap::new()))
}

#[cfg(feature = "tensorpuffer")]
fn record_prefill_tokens(seq: &vllm_rs::core::sequence::Sequence) {
    if let Ok(mut map) = runner_seq_tokens().lock() {
        map.insert(seq.id, seq.token_ids.clone());
    }
}

#[cfg(feature = "tensorpuffer")]
fn append_decoded_token(seq_id: usize, tok: u32) -> Option<Vec<u32>> {
    let mut map = runner_seq_tokens().lock().ok()?;
    let entry = map.get_mut(&seq_id)?;
    entry.push(tok);
    Some(entry.clone())
}

/// Stash post-decode KV state. Mirrors `stash_seq_kv_local` but takes
/// a `DecodeSequence` plus the precomputed running token_ids (since
/// `DecodeSequence` doesn't carry them on the wire — see
/// `RUNNER_SEQ_TOKENS`).
#[cfg(feature = "tensorpuffer")]
fn stash_decode_seq_local(
    runner: &ModelRunner,
    dseq: &vllm_rs::core::sequence::DecodeSequence,
    token_ids: &[u32],
) {
    use candle_core::DType;
    use std::collections::HashMap;
    use vllm_rs::transfer::{copy_blocks_to_cpu, cpu_tensor_to_bytes};

    if dseq.block_tables.is_empty() {
        return;
    }
    let server_block_ids = &dseq.block_tables;
    let mapping: HashMap<usize, usize> = server_block_ids
        .iter()
        .enumerate()
        .map(|(i, &server_id)| (server_id as usize, i))
        .collect();

    let gpu_cache = runner.get_kv_cache();
    if gpu_cache.is_empty() {
        return;
    }
    let dtype = gpu_cache[0].0.dtype();
    let mut layer_data: Vec<(Vec<u8>, Vec<u8>)> = Vec::with_capacity(gpu_cache.len());
    for (k_tensor, v_tensor) in gpu_cache.iter() {
        let k_cpu = match copy_blocks_to_cpu(k_tensor, &mapping, server_block_ids.len()) {
            Ok(t) => t,
            Err(err) => {
                vllm_rs::log_warn!(
                    "[kv stash] copy_blocks_to_cpu k failed for Seq {} (decode): {err}",
                    dseq.id
                );
                return;
            }
        };
        let v_cpu = match copy_blocks_to_cpu(v_tensor, &mapping, server_block_ids.len()) {
            Ok(t) => t,
            Err(err) => {
                vllm_rs::log_warn!(
                    "[kv stash] copy_blocks_to_cpu v failed for Seq {} (decode): {err}",
                    dseq.id
                );
                return;
            }
        };
        let (k_bytes, v_bytes) = match dtype {
            DType::F16 => (
                match cpu_tensor_to_bytes::<half::f16>(&k_cpu) { Ok(b) => b, Err(_) => return },
                match cpu_tensor_to_bytes::<half::f16>(&v_cpu) { Ok(b) => b, Err(_) => return },
            ),
            DType::BF16 => (
                match cpu_tensor_to_bytes::<half::bf16>(&k_cpu) { Ok(b) => b, Err(_) => return },
                match cpu_tensor_to_bytes::<half::bf16>(&v_cpu) { Ok(b) => b, Err(_) => return },
            ),
            DType::U8 => (
                match cpu_tensor_to_bytes::<u8>(&k_cpu) { Ok(b) => b, Err(_) => return },
                match cpu_tensor_to_bytes::<u8>(&v_cpu) { Ok(b) => b, Err(_) => return },
            ),
            other => {
                vllm_rs::log_warn!(
                    "[kv stash] unsupported dtype {:?} for Seq {} (decode)",
                    other,
                    dseq.id
                );
                return;
            }
        };
        layer_data.push((k_bytes, v_bytes));
    }
    drop(gpu_cache);

    let prefix_hash =
        vllm_rs::tensorpuffer_kvbm::content_hash_for_prefix("vllm-rs", token_ids);
    let stashed = vllm_rs::tensorpuffer_kvbm::stash_finished_prefill(
        dseq.id as u64,
        dseq.last_token,
        &layer_data,
        dseq.block_tables.len() as u32,
        token_ids.len() as u32,
        Some(&prefix_hash),
    );
    if std::env::var("MYELON_INSTRUMENT").map(|v| v == "1").unwrap_or(false) {
        println!(
            "[MyelonInstr] {}",
            serde_json::json!({
                "scope": "tensorpuffer_kvbm",
                "op": "stash_kv_local",
                "phase": "decode",
                "seq_id": dseq.id,
                "stashed": stashed,
                "layers": layer_data.len(),
                "blocks": dseq.block_tables.len(),
                "tokens": token_ids.len(),
                "prefix_hash": prefix_hash,
            })
        );
    }
}

fn main() -> anyhow::Result<()> {
    vllm_rs::log_info!("runner started");

    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    // Tensorpuffer KVBM init for the runner subprocess. Mirrors the
    // engine-side init in core/engine.rs so the runner has its own
    // global handle and can stash post-prefill KV without going through
    // PD. No-op when feature is off or TPUF_KVBM_ENABLE != 1.
    #[cfg(feature = "tensorpuffer")]
    {
        let _ = vllm_rs::tensorpuffer_kvbm::init_from_env();
    }
    let args: Vec<String> = std::env::args().collect();
    let sock = args
        .iter()
        .position(|s| s == "--sock")
        .and_then(|i| args.get(i + 1))
        .expect("Socket name missing");
    let uuid_str: String = args
        .iter()
        .position(|s| s == "--uuid")
        .and_then(|i| args.get(i + 1))
        .map_or("", |v| v)
        .to_string();
    let sock_name = sock.clone().to_ns_name::<GenericNamespaced>()?;
    let mut stream = LocalStream::connect(sock_name.clone());
    // shared flag for model loaded
    let model_loaded = Arc::new(AtomicBool::new(false));
    let model_loaded_ctrlc = model_loaded.clone();

    loop {
        if stream.is_ok() {
            break;
        }
        vllm_rs::log_info!("Runner retry connecting to socket: {}", sock);
        stream = LocalStream::connect(sock_name.clone());
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
    let mut stream = stream.expect("Failed to connect to socket");
    stream.write_all(b"ready\n")?;
    stream.flush()?;

    ctrlc::set_handler(move || {
        if model_loaded_ctrlc.load(Ordering::SeqCst) {
            vllm_rs::log_info!("Runner break session!");
        } else {
            vllm_rs::log_warn!("Runner break model loading (Ctrl+C detected)!");
            std::process::exit(0);
        }
    })
    .expect("Error setting Ctrl+C handler");

    vllm_rs::log_info!("Runner connected to socket: {}", sock);
    let stop_flag = Arc::new(AtomicBool::new(false));
    let _ = heartbeat_worker(None, true, stop_flag.clone(), &uuid_str);

    let msg = receive_local(&mut stream, true)?;
    let runner_rank: usize;
    let runner = match msg {
        MessageType::Init(init_req) => {
            vllm_rs::log_info!("Received init request: {:?}", init_req);
            runner_rank = init_req.rank;
            // Use init_req.rank to pick device
            let device = new_device(init_req.dev_id)?;

            #[cfg(feature = "nccl")]
            let comm = Rc::new(
                Comm::from_rank(
                    device.as_cuda_device().unwrap().cuda_device(),
                    init_req.rank,
                    init_req.num_shards,
                    init_req.nccl_id.0,
                )
                .unwrap(),
            );

            #[cfg(not(feature = "nccl"))]
            let comm = Rc::new(Comm::default());

            vllm_rs::log_info!("Loading model at rank {}", init_req.rank);

            let progress_sock_name = format!("{}@vllm-rs-progress", uuid_str);

            let progress_reporter = match RemoteProgressReporter::new(
                init_req.rank,
                init_req.num_shards,
                progress_sock_name,
                true,
            ) {
                Ok(reporter) => {
                    let reporter: Arc<RwLock<Box<dyn ProgressLike>>> =
                        Arc::new(RwLock::new(Box::new(reporter)));
                    reporter
                }
                _ => {
                    vllm_rs::log_error!("Unable to create remote progress reporter!");
                    let reporter: Arc<RwLock<Box<dyn ProgressLike>>> =
                        Arc::new(RwLock::new(Box::new(ProgressReporter::new(init_req.rank))));
                    reporter
                }
            };

            let (transfer, is_pd_server) = if let Some(t_cfg) = &init_req.econfig.pd_config {
                (
                    Some(Arc::new(Transfer::new(
                        t_cfg.clone(),
                        init_req.rank,
                        model_loaded.clone(),
                        stop_flag.clone(),
                    )?)),
                    matches!(t_cfg.role, PdRole::Server),
                )
            } else {
                (None, false)
            };

            let stream_kv = Some(stream.try_clone()?);
            let mut econfig = init_req.econfig.clone();
            let tokenizer_path = init_req.model_pathes.get_tokenizer_filename();
            let llg_factory = if init_req.is_gguf {
                match load_gguf_info_from_files(&init_req.model_pathes.get_weight_filenames()) {
                    Ok(info) => match build_llg_factory(info.tokenizer, init_req.config.vocab_size)
                    {
                        Ok(f) => Some(f),
                        Err(e) => {
                            vllm_rs::log_warn!("Failed to build llguidance factory: {}", e);
                            None
                        }
                    },
                    Err(e) => {
                        vllm_rs::log_warn!(
                            "Failed to load GGUF tokenizer metadata; disabling optional llguidance: {}",
                            e
                        );
                        None
                    }
                }
            } else if tokenizer_path.exists() {
                match Tokenizer::from_file(&tokenizer_path) {
                    Ok(tokenizer) => match build_llg_factory(tokenizer, init_req.config.vocab_size)
                    {
                        Ok(f) => Some(f),
                        Err(e) => {
                            vllm_rs::log_warn!("Failed to build llguidance factory: {}", e);
                            None
                        }
                    },
                    Err(e) => {
                        vllm_rs::log_warn!(
                            "Failed to load tokenizer from {:?}; disabling optional llguidance: {}",
                            tokenizer_path,
                            e
                        );
                        None
                    }
                }
            } else {
                vllm_rs::log_warn!(
                    "Tokenizer file {:?} not found; disabling optional llguidance",
                    tokenizer_path
                );
                None
            };
            #[allow(unused_mut)]
            let mut runner = {
                let _guard = candle_core::InferenceMode::enter();
                let vb = VarBuilderX::new(
                    &init_req.model_pathes,
                    init_req.is_gguf,
                    init_req.dtype.into(),
                    &device,
                )?;
                let runner = ModelRunner::new(
                    init_req.model_type,
                    &vb,
                    comm,
                    &mut econfig,
                    &init_req.config,
                    init_req.dtype.into(),
                    init_req.is_rope_i,
                    device,
                    progress_reporter,
                    transfer,
                    llg_factory,
                    stream_kv,
                )?;
                drop(vb);
                runner
            };

            vllm_rs::log_info!(
                "Runner at rank {} created (PD config: {:?})!",
                init_req.rank,
                init_req.econfig.pd_config
            );

            // Optional warmup
            if !is_pd_server {
                //No need graph capture for PD server
                #[cfg(all(feature = "cuda", feature = "graph"))]
                let arch = init_req.config.architectures.as_ref().unwrap()[0].clone();
                #[cfg(all(feature = "cuda", feature = "graph"))]
                if vllm_rs::utils::is_no_cuda_graph_supprt(arch.clone()) {
                    vllm_rs::log_info!("{arch} does not supprt CUDA graph");
                } else {
                    match runner.warmup_capture() {
                        Ok(_) => {
                            use colored::Colorize;
                            eprintln!("{}", String::from("Cuda graph captured").yellow());
                        }
                        Err(e) => {
                            use colored::Colorize;
                            let s = format!("Graph capture failed: {:?}", e);
                            eprintln!("{}", s.red());
                        }
                    }
                }
            }

            send_local(
                &mut vec![stream.try_clone()?],
                &MessageType::InitAck(true),
                false,
            )?;
            runner
        }
        _ => {
            vllm_rs::log_error!("Unexpected message type: {:?}", msg);
            panic!("Unexpected message type");
        }
    };

    // mark model as loaded
    model_loaded.store(true, Ordering::SeqCst);
    #[cfg(feature = "myelon")]
    let mut myelon_transport: Option<(
        RpcBroadcastConsumer,
        ResponseProducer,
        MyelonTransportAccessMode,
    )> = None;

    loop {
        match receive_local(&mut stream, false) {
            #[cfg(feature = "myelon")]
            Ok(MessageType::InitMyelonTransport(config)) => {
                vllm_rs::log_info!(
                    "Runner configuring Myelon transport rpc={} resp={}",
                    config.rpc_ring_name,
                    config.response_ring_name
                );
                vllm_rs::log_warn!(
                    "Runner switching execution to Myelon hot path; legacy local-socket control handling will stop after this handshake."
                );
                let rpc_consumer = match (config.backend, config.access_mode) {
                    (MyelonTransportBackend::Shm, MyelonTransportAccessMode::Typed) => {
                        RpcBroadcastConsumer::attach_typed_shm(
                            &config.rpc_ring_name,
                            config.rpc_depth,
                            config.wait_strategy,
                        )
                    }
                    (MyelonTransportBackend::Shm, _) => RpcBroadcastConsumer::attach_shm(
                        &config.rpc_ring_name,
                        config.rpc_depth,
                        config.wait_strategy,
                    ),
                    (MyelonTransportBackend::Mmap, MyelonTransportAccessMode::Typed) => {
                        RpcBroadcastConsumer::attach_typed_mmap(
                            myelon_playground::MmapTransportLayout::new(
                                config.mmap_root_dir()?,
                                config.rpc_ring_name.clone(),
                            )?,
                            config.rpc_depth,
                            &format!("runner-rpc-{}", config.rank),
                            config.wait_strategy,
                        )
                    }
                    (MyelonTransportBackend::Mmap, _) => RpcBroadcastConsumer::attach_mmap(
                        myelon_playground::MmapTransportLayout::new(
                            config.mmap_root_dir()?,
                            config.rpc_ring_name.clone(),
                        )?,
                        config.rpc_depth,
                        &format!("runner-rpc-{}", config.rank),
                        config.wait_strategy,
                    ),
                }?;
                let response_producer = match (config.backend, config.access_mode) {
                    (MyelonTransportBackend::Shm, MyelonTransportAccessMode::Typed) => {
                        ResponseProducer::create_typed_shm(
                            &config.response_ring_name,
                            config.response_depth,
                        )
                    }
                    (MyelonTransportBackend::Shm, _) => ResponseProducer::create_shm(
                        &config.response_ring_name,
                        config.response_depth,
                    ),
                    (MyelonTransportBackend::Mmap, MyelonTransportAccessMode::Typed) => {
                        ResponseProducer::create_typed_mmap(
                            myelon_playground::MmapTransportLayout::new(
                                config.mmap_root_dir()?,
                                config.response_ring_name.clone(),
                            )?,
                            config.response_depth,
                        )
                    }
                    (MyelonTransportBackend::Mmap, _) => ResponseProducer::create_mmap(
                        myelon_playground::MmapTransportLayout::new(
                            config.mmap_root_dir()?,
                            config.response_ring_name.clone(),
                        )?,
                        config.response_depth,
                    ),
                }?;
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::MyelonReady,
                    false,
                )?;
                myelon_transport = Some((rpc_consumer, response_producer, config.access_mode));
                break;
            }
            Ok(MessageType::Shutdown) => {
                vllm_rs::log_info!("Runner exit");
                break;
            }
            Ok(MessageType::RunPrefill((sequences, is_prefill))) => {
                // Tensorpuffer KVBM try-load: BEFORE prefill, look up
                // each seq's content hash in the puffer. On hit, write
                // the bytes directly into this runner's KV cache and
                // bump seq.num_cached_tokens so the engine's existing
                // prefix-cache logic skips the cached prefix on the
                // upcoming prefill compute. Off by default; enable
                // with TPUF_KVBM_TRY_LOAD=1.
                let mut sequences = sequences;
                #[cfg(feature = "tensorpuffer")]
                let try_load_on = try_load_enabled();
                #[cfg(feature = "tensorpuffer")]
                if try_load_on && is_prefill {
                    for seq in sequences.iter_mut() {
                        let _ = try_import_seq_kv_from_puffer(&runner, seq);
                    }
                }

                let outputs = runner.run(
                    Seqs::SeqRefs(&sequences.iter().collect::<Vec<_>>()),
                    is_prefill,
                );
                if outputs.is_err() {
                    vllm_rs::log_error!("Runner prefill error: {:?}", outputs);
                }
                // Tensorpuffer KVBM: durably stash every successfully
                // prefilled seq under content-addressed key. Best-effort,
                // gated by TPUF_KVBM_ENABLE so non-PD single-engine
                // workloads can survive a restart.
                #[cfg(feature = "tensorpuffer")]
                if outputs.is_ok() && is_prefill {
                    for seq in &sequences {
                        // Snapshot token_ids so the decode-side stash
                        // can rebuild a content hash later.
                        record_prefill_tokens(seq);
                        stash_seq_kv_local(&runner, seq, "prefill");
                    }
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::RunResponse(outputs.unwrap_or(vec![])),
                    false,
                )?;
            }
            Ok(MessageType::RunDecode((sequences, is_prefill))) => {
                let outputs = runner.run(Seqs::DecodeVec(&sequences), is_prefill);
                if outputs.is_err() {
                    vllm_rs::log_error!("Runner decode error: {:?}", outputs);
                }
                // Tensorpuffer KVBM: optional decode-side stash. Each
                // call captures the current KV state under a content
                // hash that includes the just-emitted token, so the
                // stashed snapshots form a chain prompt → prompt+1 →
                // prompt+2 → … and a restart can rejoin at the deepest
                // matching prefix. Off by default — enable with
                // `TPUF_KVBM_STASH_DECODE=1`.
                //
                // RunDecode messages carry a stripped `DecodeSequence`
                // (no token_ids on the wire). We rebuild the running
                // token list from the per-seq cache populated during
                // RunPrefill. If a seq's prefill happened on a different
                // runner process (PD-disagg) the cache lookup will miss
                // and we silently skip — the prefill side already
                // stashed.
                #[cfg(feature = "tensorpuffer")]
                if outputs.is_ok() && decode_stash_enabled() {
                    for dseq in &sequences {
                        if let Some(token_ids) =
                            append_decoded_token(dseq.id, dseq.last_token)
                        {
                            stash_decode_seq_local(&runner, dseq, &token_ids);
                        }
                    }
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::RunResponse(outputs.unwrap_or(vec![])),
                    false,
                )?;
            }
            Ok(MessageType::RunEmbed((sequences, strategy))) => {
                use vllm_rs::core::sequence::Sequence;
                let refs: Vec<&Sequence> = sequences.iter().collect();
                let slice: &[&Sequence] = &refs;
                let outputs = runner.embed(&slice, &strategy);
                if outputs.is_err() {
                    vllm_rs::log_error!("Runner embedding error: {:?}", outputs);
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::RunResponseEmbed(outputs.unwrap_or(vec![vec![]])),
                    false,
                )?;
            }
            Ok(MessageType::LoadingProgress(_)) => {
                vllm_rs::log_info!("Received loading progress message");
            }
            Ok(MessageType::KVCacheSwap((mappings, swap_in))) => {
                vllm_rs::log_info!(
                    "Received KVCacheSwap message: {} kv cache blocks need to {}!",
                    mappings.len(),
                    if swap_in { "swap in" } else { "swap out" },
                );
                let ret = runner.swap_kvcache(mappings, swap_in);
                if ret.is_err() {
                    vllm_rs::log_error!("KvCache Swap failed: {:?}", ret);
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::KVCacheSwapResponse(ret.is_ok()),
                    false,
                )?;
            }
            Ok(MessageType::FinishDecode(id)) => {
                runner.finished(id);
            }
            Ok(MessageType::CaptureMambaPrefixState((seq_id, hash, preserve))) => {
                let ret = runner.capture_mamba_prefix_state(seq_id, hash, preserve);
                if ret.is_err() {
                    vllm_rs::log_error!(
                        "CaptureMambaPrefixState failed for seq {} hash {} preserve={} : {:?}",
                        seq_id,
                        hash,
                        preserve,
                        ret
                    );
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::CaptureMambaPrefixStateResponse(ret.unwrap_or(false)),
                    false,
                )?;
            }
            Ok(MessageType::HasMambaPrefixState(hash)) => {
                let ret = runner.has_mamba_prefix_state(hash);
                if ret.is_err() {
                    vllm_rs::log_error!("HasMambaPrefixState failed for hash {}: {:?}", hash, ret);
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::HasMambaPrefixStateResponse(ret.unwrap_or(false)),
                    false,
                )?;
            }
            Ok(MessageType::TransferPrefill(sequence)) => {
                let ret = runner.transfer_prefill(&sequence);
                // if ret.is_err() {
                //     vllm_rs::log_error!("Prefill transfer failed: {:?}", ret);
                // }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::TransferPrefillResponse(ret.is_ok()),
                    false,
                )?;
            }
            Ok(MessageType::ReceivePrefill(id)) => {
                let ret = runner.try_receive_prefill(id);
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::ReceivePrefillResponse(ret.unwrap_or((false, None))),
                    false,
                )?;
            }
            Ok(MessageType::CheckPrefillStatus(id)) => {
                let status = runner.check_prefill_status(id);
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::CheckPrefillStatusResponse(
                        status.is_ok() && status.unwrap_or(false),
                    ),
                    false,
                )?;
            }
            Ok(MessageType::KvCacheSend((sequence, token))) => {
                vllm_rs::log_info!(
                    "Runner received KvCacheSend for seq {} (first_token={}).",
                    sequence.id,
                    token
                );
                let ret = runner.send_kvcache(&sequence, token);
                if ret.is_err() {
                    vllm_rs::log_error!("KvCacheSend failed: {:?}", ret);
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::KvCacheSendResponse(ret.is_ok()),
                    false,
                )?;
            }
            Ok(MessageType::KvCacheReceive(sequence)) => {
                let ret = runner.receive_kvcache(&sequence);
                if ret.is_err() {
                    vllm_rs::log_error!("KvCacheReceive failed: {:?}", ret);
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::KvCacheReceiveResponse(ret.unwrap_or((false, 0, 0, 0))),
                    false,
                )?;
            }
            Ok(MessageType::KvCacheRelease(id)) => {
                let status = runner.release_remote_kvcache(id);
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::KvCacheReleaseResponse(status.is_ok() && status.unwrap_or(false)),
                    false,
                )?;
            }
            Ok(MessageType::CheckKvCacheRelease(id)) => {
                let status = runner.check_kvcache_release(id);
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::CheckKvCacheReleaseResponse(
                        status.is_ok() && status.unwrap_or(false),
                    ),
                    false,
                )?;
            }
            Ok(MessageType::ClearBlocks(block_ids)) => {
                let ret = runner.clear_blocks(block_ids);
                if ret.is_err() {
                    vllm_rs::log_error!("ClearBlocks failed: {:?}", ret);
                }
                send_local(
                    &mut vec![stream.try_clone()?],
                    &MessageType::ClearBlocksResponse(ret.is_ok()),
                    false,
                )?;
            }
            Err(e) => {
                if e.kind() != std::io::ErrorKind::UnexpectedEof {
                    vllm_rs::log_error!("Runner exit with error: {:?}", e);
                }
                break;
            }
            _ => {
                vllm_rs::log_error!("Unexpected message type");
            }
        }
    }

    #[cfg(feature = "myelon")]
    if let Some((mut rpc_consumer, mut response_producer, access_mode)) = myelon_transport {
        let mut logged_first_rpc = false;
        let mut logged_first_response = false;
        loop {
            // RFC 0034 P2.4: under Typed mode, dispatch RunPrefill INSIDE the
            // lease closure to skip the owned `Vec<Sequence>` materialisation.
            // The closure returns either:
            //   - `None` if the request was handled inline (RunPrefill zero-copy
            //     path); the outer match below is then a no-op for this iteration.
            //   - `Some((id, owned_request))` for every other request kind, which
            //     falls through to the owned-dispatch match the same way as
            //     Owned/Borrowed access modes do.
            //
            // Only RunPrefill goes zero-copy — it has the largest payload
            // (Vec<Sequence>) and is the dominant cost on prefill-heavy workloads.
            // RunDecode and the small-payload control-plane requests stay on the
            // owned path because the savings would be sub-microsecond and the
            // structural complexity (decode Seqs::ArchivedDecodeSeqs through
            // sample(), prepare_decode, KV ring etc.) is much larger.
            #[cfg(feature = "codec-rkyv")]
            let typed_inline_dispatch =
                |runner: &ModelRunner,
                 response_producer: &mut ResponseProducer,
                 logged_first_rpc: &mut bool,
                 logged_first_response: &mut bool,
                 id: u64,
                 borrowed: BorrowedTypedMyelonRequest<'_>|
                 -> candle_core::Result<Option<(u64, MyelonRequest)>> {
                    match borrowed {
                        BorrowedTypedMyelonRequest::RunPrefill { sequences, .. } => {
                            if !*logged_first_rpc {
                                vllm_rs::log_info!(
                                    "Runner entered Myelon hot path (typed zero-copy prefill) request_id={}.",
                                    id,
                                );
                                *logged_first_rpc = true;
                            }
                            let outputs =
                                runner.run(Seqs::ArchivedSeqs(sequences), true)?;
                            if runner_rank == 0 {
                                let response = MyelonResponse::RunResponse(outputs);
                                if !*logged_first_response {
                                    vllm_rs::log_info!(
                                        "Runner sent first Myelon response (typed) kind={} request_id={}.",
                                        response.kind().as_u8(),
                                        id,
                                    );
                                    *logged_first_response = true;
                                }
                                response_producer
                                    .send_response(&response, id)
                                    .expect("serialize Myelon prefill outputs (typed zero-copy)");
                            }
                            Ok(None)
                        }
                        // RFC 0034 P2.5: zero-copy decode dispatch — same
                        // pattern as RunPrefill but using ArchivedDecodeSeqs.
                        // Decode payloads are smaller per request than prefill
                        // (no token_ids, just block_tables), but every decode
                        // step pays them, so the aggregate saving across long
                        // generation runs is worth it.
                        BorrowedTypedMyelonRequest::RunDecode { sequences, .. } => {
                            let outputs =
                                runner.run(Seqs::ArchivedDecodeSeqs(sequences), false)?;
                            if runner_rank == 0 {
                                let response = MyelonResponse::RunResponse(outputs);
                                response_producer
                                    .send_response(&response, id)
                                    .expect("serialize Myelon decode outputs (typed zero-copy)");
                            }
                            Ok(None)
                        }
                        // RFC 0034 T1.3 — small-payload kinds with no
                        // sequence body. These avoid the to_owned() →
                        // outer-match round-trip; the payload is just one
                        // primitive (sequence_id or available_tokens) so the
                        // saving per request is sub-µs, but the consistency
                        // matters: the typed path is now fully self-contained
                        // for every request kind.
                        //
                        // No-response variants (FinishDecode, Cancel) just
                        // call the runner method.
                        BorrowedTypedMyelonRequest::FinishDecode { sequence_id, .. }
                        | BorrowedTypedMyelonRequest::Cancel { sequence_id, .. } => {
                            runner.finished(sequence_id);
                            Ok(None)
                        }
                        BorrowedTypedMyelonRequest::ReceivePrefill {
                            available_tokens,
                            ..
                        } => {
                            let response = match runner
                                .try_receive_prefill(available_tokens)
                            {
                                Ok(value) => MyelonResponse::ReceivePrefillResponse(value),
                                Err(error) => {
                                    response_producer.send_error(error, id);
                                    return Ok(None);
                                }
                            };
                            response_producer
                                .send_response(&response, id)
                                .expect("serialize Myelon receive prefill (typed)");
                            Ok(None)
                        }
                        BorrowedTypedMyelonRequest::CheckPrefillStatus {
                            sequence_id,
                            ..
                        } => {
                            let response = match runner.check_prefill_status(sequence_id) {
                                Ok(value) => MyelonResponse::CheckPrefillStatusResponse(value),
                                Err(error) => {
                                    response_producer.send_error(error, id);
                                    return Ok(None);
                                }
                            };
                            response_producer
                                .send_response(&response, id)
                                .expect("serialize Myelon check prefill status (typed)");
                            Ok(None)
                        }
                        BorrowedTypedMyelonRequest::KvCacheRelease { sequence_id, .. } => {
                            let response = match runner.release_remote_kvcache(sequence_id) {
                                Ok(value) => MyelonResponse::KvCacheReleaseResponse(value),
                                Err(error) => {
                                    response_producer.send_error(error, id);
                                    return Ok(None);
                                }
                            };
                            response_producer
                                .send_response(&response, id)
                                .expect("serialize Myelon kv release (typed)");
                            Ok(None)
                        }
                        BorrowedTypedMyelonRequest::CheckKvCacheRelease {
                            sequence_id,
                            ..
                        } => {
                            let response = match runner.check_kvcache_release(sequence_id) {
                                Ok(value) => MyelonResponse::CheckKvCacheReleaseResponse(value),
                                Err(error) => {
                                    response_producer.send_error(error, id);
                                    return Ok(None);
                                }
                            };
                            response_producer
                                .send_response(&response, id)
                                .expect("serialize Myelon check kv release (typed)");
                            Ok(None)
                        }
                        // Sequence-bearing variants (TransferPrefill,
                        // KvCacheSend, KvCacheReceive, KvCacheSwap) carry
                        // archived Sequence payloads that the existing runner
                        // methods take by &Sequence — no zero-copy without
                        // refactoring those signatures (out of P2 scope).
                        // Materialise to owned + outer match handles them.
                        // Shutdown also goes through the outer path so the
                        // hot loop's break logic applies.
                        other => {
                            let owned = other
                                .to_owned()
                                .map_err(|e| candle_core::Error::Msg(e.to_string()))?;
                            Ok(Some((id, owned)))
                        }
                    }
                };

            let pair = match access_mode {
                MyelonTransportAccessMode::Owned => match rpc_consumer
                    .recv_request_blocking_owned()
                {
                    Ok(p) => Some(p),
                    Err(error) => {
                        response_producer.send_error(error, 0);
                        continue;
                    }
                },
                MyelonTransportAccessMode::Borrowed => match rpc_consumer
                    .recv_request_blocking_borrowed()
                {
                    Ok(p) => Some(p),
                    Err(error) => {
                        response_producer.send_error(error, 0);
                        continue;
                    }
                },
                MyelonTransportAccessMode::Typed => {
                    #[cfg(feature = "codec-rkyv")]
                    {
                        let result = rpc_consumer.with_request_blocking_typed(
                            |id, borrowed| {
                                typed_inline_dispatch(
                                    &runner,
                                    &mut response_producer,
                                    &mut logged_first_rpc,
                                    &mut logged_first_response,
                                    id,
                                    borrowed,
                                )
                            },
                        );
                        match result {
                            Ok(None) => continue, // handled inline (zero-copy prefill)
                            Ok(Some(p)) => Some(p),
                            Err(error) => {
                                response_producer.send_error(error, 0);
                                continue;
                            }
                        }
                    }
                    #[cfg(not(feature = "codec-rkyv"))]
                    {
                        // Without rkyv, Typed mode has no zero-copy path; fall
                        // back to the previous to_owned() behaviour so the
                        // outer match handles the request normally.
                        match rpc_consumer.with_request_blocking_typed(
                            |id, request| {
                                request
                                    .to_owned()
                                    .map(|owned| (id, owned))
                                    .map_err(|e| candle_core::Error::Msg(e.to_string()))
                            },
                        ) {
                            Ok(p) => Some(p),
                            Err(error) => {
                                response_producer.send_error(error, 0);
                                continue;
                            }
                        }
                    }
                }
            };
            let (request_id, request) = match pair {
                Some(p) => p,
                None => continue,
            };
            if !logged_first_rpc {
                vllm_rs::log_info!(
                    "Runner entered Myelon hot path with first kind={} request_id={}.",
                    request.kind().as_u8(),
                    request_id,
                );
                logged_first_rpc = true;
            }
            match request {
                MyelonRequest::RunPrefill { sequences } => {
                    let refs = sequences.iter().collect::<Vec<_>>();
                    match runner.run(Seqs::SeqRefs(&refs), true) {
                        Ok(outputs) => {
                            if runner_rank == 0 {
                                let response = MyelonResponse::RunResponse(outputs);
                                if !logged_first_response {
                                    vllm_rs::log_info!(
                                        "Runner sent first Myelon response kind={} request_id={}.",
                                        response.kind().as_u8(),
                                        request_id,
                                    );
                                    logged_first_response = true;
                                }
                                response_producer
                                    .send_response(&response, request_id)
                                    .expect("serialize Myelon prefill outputs");
                            }
                        }
                        Err(error) => {
                            if runner_rank == 0 {
                                response_producer.send_error(error, request_id);
                            }
                        }
                    }
                }
                MyelonRequest::RunDecode { sequences } => {
                    match runner.run(Seqs::DecodeVec(&sequences), false) {
                        Ok(outputs) => {
                            if runner_rank == 0 {
                                let response = MyelonResponse::RunResponse(outputs);
                                if !logged_first_response {
                                    vllm_rs::log_info!(
                                        "Runner sent first Myelon response kind={} request_id={}.",
                                        response.kind().as_u8(),
                                        request_id,
                                    );
                                    logged_first_response = true;
                                }
                                response_producer
                                    .send_response(&response, request_id)
                                    .expect("serialize Myelon decode outputs");
                            }
                        }
                        Err(error) => {
                            if runner_rank == 0 {
                                response_producer.send_error(error, request_id);
                            }
                        }
                    }
                }
                MyelonRequest::FinishDecode { sequence_id }
                | MyelonRequest::Cancel { sequence_id } => {
                    runner.finished(sequence_id);
                }
                MyelonRequest::TransferPrefill { sequence } => {
                    let response = match runner.transfer_prefill(&sequence) {
                        Ok(value) => MyelonResponse::TransferPrefillResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon transfer prefill response");
                }
                MyelonRequest::ReceivePrefill { available_tokens } => {
                    let response = match runner.try_receive_prefill(available_tokens) {
                        Ok(value) => MyelonResponse::ReceivePrefillResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon receive prefill response");
                }
                MyelonRequest::CheckPrefillStatus { sequence_id } => {
                    let response = match runner.check_prefill_status(sequence_id) {
                        Ok(value) => MyelonResponse::CheckPrefillStatusResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon check prefill status response");
                }
                MyelonRequest::KvCacheSend {
                    sequence,
                    first_token,
                } => {
                    vllm_rs::log_info!(
                        "Runner received Myelon KvCacheSend for seq {} (first_token={}, request_id={}).",
                        sequence.id,
                        first_token,
                        request_id,
                    );
                    let response = match runner.send_kvcache(&sequence, first_token) {
                        Ok(value) => MyelonResponse::KvCacheSendResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon kv cache send response");
                }
                MyelonRequest::KvCacheReceive { sequence } => {
                    let response = match runner.receive_kvcache(&sequence) {
                        Ok(value) => MyelonResponse::KvCacheReceiveResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon kv cache receive response");
                }
                MyelonRequest::KvCacheRelease { sequence_id } => {
                    let response = match runner.release_remote_kvcache(sequence_id) {
                        Ok(value) => MyelonResponse::KvCacheReleaseResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon kv cache release response");
                }
                MyelonRequest::CheckKvCacheRelease { sequence_id } => {
                    let response = match runner.check_kvcache_release(sequence_id) {
                        Ok(value) => MyelonResponse::CheckKvCacheReleaseResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon kv cache release status response");
                }
                MyelonRequest::KvCacheSwap { mappings, swap_in } => {
                    let response = match runner.swap_kvcache(mappings, swap_in) {
                        Ok(value) => MyelonResponse::KvCacheSwapResponse(value),
                        Err(error) => {
                            response_producer.send_error(error, request_id);
                            continue;
                        }
                    };
                    response_producer
                        .send_response(&response, request_id)
                        .expect("serialize Myelon kv cache swap response");
                }
                MyelonRequest::Shutdown => {
                    vllm_rs::log_info!("Runner received Myelon shutdown.");
                    break;
                }
            }
        }
    }

    stop_flag.store(true, Ordering::Relaxed);
    vllm_rs::log_info!("Runner finished");
    std::process::exit(0);
}
