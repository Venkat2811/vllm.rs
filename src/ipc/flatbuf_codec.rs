//! FlatBuffers-based serialization for Myelon IPC messages.
//! Enabled by the `myelon-flatbuf` feature flag.
#![cfg(feature = "myelon-flatbuf")]

use crate::core::sequence::{
    DecodeSequence as RustDecodeSequence, Sequence as RustSequence,
    SequenceStatus as RustSequenceStatus,
};
use crate::ipc::myelon_ipc::{MsgKind, MyelonRequest, MyelonResponse};
use crate::ipc::schema;
use crate::utils::config::SamplingParams as RustSamplingParams;
use crate::utils::image::ImageData as RustImageData;
use candle_core::Result as CandleResult;
use flatbuffers::FlatBufferBuilder;
use std::collections::HashMap;

fn fb_err(msg: &str) -> candle_core::Error {
    candle_core::Error::Msg(format!("flatbuf: {msg}"))
}

// ---------------------------------------------------------------------------
// Domain → FlatBuffer helpers
// ---------------------------------------------------------------------------

fn status_to_fb(s: &RustSequenceStatus) -> schema::SequenceStatus {
    match s {
        RustSequenceStatus::Waiting => schema::SequenceStatus::Waiting,
        RustSequenceStatus::Running => schema::SequenceStatus::Running,
        RustSequenceStatus::Finished => schema::SequenceStatus::Finished,
        RustSequenceStatus::Cached => schema::SequenceStatus::Cached,
        RustSequenceStatus::Swapped => schema::SequenceStatus::Swapped,
        RustSequenceStatus::FinishSwapped => schema::SequenceStatus::FinishSwapped,
    }
}

fn status_from_fb(s: schema::SequenceStatus) -> RustSequenceStatus {
    match s {
        schema::SequenceStatus::Running => RustSequenceStatus::Running,
        schema::SequenceStatus::Finished => RustSequenceStatus::Finished,
        schema::SequenceStatus::Cached => RustSequenceStatus::Cached,
        schema::SequenceStatus::Swapped => RustSequenceStatus::Swapped,
        schema::SequenceStatus::FinishSwapped => RustSequenceStatus::FinishSwapped,
        _ => RustSequenceStatus::Waiting,
    }
}

fn build_sampling_params<'a>(
    fbb: &mut FlatBufferBuilder<'a>,
    sp: &RustSamplingParams,
) -> flatbuffers::WIPOffset<schema::SamplingParams<'a>> {
    let session_id = sp.session_id.as_deref().map(|s| fbb.create_string(s));
    let grammar_json = sp.grammar_json.as_deref().map(|s| fbb.create_string(s));

    let stop_seqs = sp.stop_sequences.as_ref().map(|seqs| {
        let offsets: Vec<_> = seqs.iter().map(|s| fbb.create_string(s)).collect();
        fbb.create_vector(&offsets)
    });

    schema::SamplingParams::create(
        fbb,
        &schema::SamplingParamsArgs {
            temperature: sp.temperature.unwrap_or(0.0),
            has_temperature: sp.temperature.is_some(),
            max_tokens: sp.max_tokens.unwrap_or(0) as u64,
            has_max_tokens: sp.max_tokens.is_some(),
            ignore_eos: sp.ignore_eos,
            top_k: sp.top_k.unwrap_or(0) as i64,
            has_top_k: sp.top_k.is_some(),
            top_p: sp.top_p.unwrap_or(0.0),
            has_top_p: sp.top_p.is_some(),
            session_id,
            frequency_penalty: sp.frequency_penalty.unwrap_or(0.0),
            has_frequency_penalty: sp.frequency_penalty.is_some(),
            presence_penalty: sp.presence_penalty.unwrap_or(0.0),
            has_presence_penalty: sp.presence_penalty.is_some(),
            stop_sequences: stop_seqs,
            thinking: sp.thinking.unwrap_or(false),
            has_thinking: sp.thinking.is_some(),
            mcp_mode: sp.mcp_mode.unwrap_or(false),
            has_mcp_mode: sp.mcp_mode.is_some(),
            grammar_json,
        },
    )
}

fn parse_sampling_params(fb: &schema::SamplingParams<'_>) -> RustSamplingParams {
    let stop_sequences = fb.stop_sequences().map(|v| {
        (0..v.len()).map(|i| v.get(i).to_string()).collect()
    });

    RustSamplingParams {
        temperature: if fb.has_temperature() {
            Some(fb.temperature())
        } else {
            None
        },
        max_tokens: if fb.has_max_tokens() {
            Some(fb.max_tokens() as usize)
        } else {
            None
        },
        ignore_eos: fb.ignore_eos(),
        top_k: if fb.has_top_k() {
            Some(fb.top_k() as isize)
        } else {
            None
        },
        top_p: if fb.has_top_p() {
            Some(fb.top_p())
        } else {
            None
        },
        session_id: fb.session_id().map(|s| s.to_string()),
        frequency_penalty: if fb.has_frequency_penalty() {
            Some(fb.frequency_penalty())
        } else {
            None
        },
        presence_penalty: if fb.has_presence_penalty() {
            Some(fb.presence_penalty())
        } else {
            None
        },
        stop_sequences,
        stop_token_ids: None,
        thinking: if fb.has_thinking() {
            Some(fb.thinking())
        } else {
            None
        },
        mcp_mode: if fb.has_mcp_mode() {
            Some(fb.mcp_mode())
        } else {
            None
        },
        grammar: None,
        grammar_json: fb.grammar_json().map(|s| s.to_string()),
        reasoning_effort: None,
    }
}

fn build_image_data<'a>(
    fbb: &mut FlatBufferBuilder<'a>,
    img: &RustImageData,
) -> flatbuffers::WIPOffset<schema::ImageData<'a>> {
    let raw = fbb.create_vector(&img.raw);
    let shape: Vec<u64> = img.shape.iter().map(|&v| v as u64).collect();
    let shape_vec = fbb.create_vector(&shape);
    let patches_first: Vec<u64> = img.patches.iter().map(|p| p.0 as u64).collect();
    let patches_second: Vec<u64> = img.patches.iter().map(|p| p.1 as u64).collect();
    let pf = fbb.create_vector(&patches_first);
    let ps = fbb.create_vector(&patches_second);
    let tpi: Vec<u64> = img.tokens_per_image.iter().map(|&v| v as u64).collect();
    let tpi_vec = fbb.create_vector(&tpi);

    schema::ImageData::create(
        fbb,
        &schema::ImageDataArgs {
            raw: Some(raw),
            shape: Some(shape_vec),
            patches_first: Some(pf),
            patches_second: Some(ps),
            image_idx: img.image_idx,
            image_token_offset: img.image_token_offset as u64,
            tokens_per_image: Some(tpi_vec),
            image_token_id: img.image_token_id.unwrap_or(0),
            has_image_token_id: img.image_token_id.is_some(),
        },
    )
}

fn parse_image_data(fb: &schema::ImageData<'_>) -> RustImageData {
    let raw = fb.raw().map(|v| v.bytes().to_vec()).unwrap_or_default();
    let shape = fb
        .shape()
        .map(|v| v.iter().map(|x| x as usize).collect())
        .unwrap_or_default();
    let patches_first: Vec<usize> = fb
        .patches_first()
        .map(|v| v.iter().map(|x| x as usize).collect())
        .unwrap_or_default();
    let patches_second: Vec<usize> = fb
        .patches_second()
        .map(|v| v.iter().map(|x| x as usize).collect())
        .unwrap_or_default();
    let patches: Vec<(usize, usize)> = patches_first
        .into_iter()
        .zip(patches_second)
        .collect();
    let tokens_per_image = fb
        .tokens_per_image()
        .map(|v| v.iter().map(|x| x as usize).collect())
        .unwrap_or_default();
    let image_token_id = if fb.has_image_token_id() {
        Some(fb.image_token_id())
    } else {
        None
    };

    RustImageData {
        raw,
        shape,
        patches,
        image_idx: fb.image_idx(),
        image_token_offset: fb.image_token_offset() as usize,
        tokens_per_image,
        image_token_id,
    }
}

fn build_sequence<'a>(
    fbb: &mut FlatBufferBuilder<'a>,
    seq: &RustSequence,
) -> flatbuffers::WIPOffset<schema::Sequence<'a>> {
    let sp = build_sampling_params(fbb, &seq.sampling_params);
    let token_ids = fbb.create_vector(&seq.token_ids);
    let output_ids = fbb.create_vector(&seq.output_ids);
    let block_table = fbb.create_vector(&seq.block_table);
    let images = seq.images.as_ref().map(|img| build_image_data(fbb, img));
    let stop_seq = seq.stop_sequence.as_deref().map(|s| fbb.create_string(s));

    schema::Sequence::create(
        fbb,
        &schema::SequenceArgs {
            id: seq.id as u64,
            created_time: seq.created_time as u64,
            swapped_time: seq.swapped_time.unwrap_or(0) as u64,
            has_swapped_time: seq.swapped_time.is_some(),
            status: status_to_fb(&seq.status),
            token_ids: Some(token_ids),
            output_ids: Some(output_ids),
            block_table: Some(block_table),
            num_cached_tokens: seq.num_cached_tokens as u64,
            mamba_prefix_hash: seq.mamba_prefix_hash.unwrap_or(0),
            has_mamba_prefix_hash: seq.mamba_prefix_hash.is_some(),
            last_token: seq.last_token,
            block_size: seq.block_size as u64,
            sampling_params: Some(sp),
            pd_first_token: seq.pd_first_token.unwrap_or(0),
            has_pd_first_token: seq.pd_first_token.is_some(),
            images,
            is_tool_call_end: seq.is_tool_call_end,
            hit_stop_sequence: seq.hit_stop_sequence,
            stop_sequence: stop_seq,
        },
    )
}

fn parse_sequence(fb: &schema::Sequence<'_>) -> CandleResult<RustSequence> {
    let sp = fb
        .sampling_params()
        .map(|s| parse_sampling_params(&s))
        .ok_or_else(|| fb_err("missing sampling_params in Sequence"))?;

    Ok(RustSequence {
        id: fb.id() as usize,
        created_time: fb.created_time() as usize,
        swapped_time: if fb.has_swapped_time() {
            Some(fb.swapped_time() as usize)
        } else {
            None
        },
        status: status_from_fb(fb.status()),
        token_ids: fb
            .token_ids()
            .map(|v| v.iter().collect())
            .unwrap_or_default(),
        output_ids: fb
            .output_ids()
            .map(|v| v.iter().collect())
            .unwrap_or_default(),
        block_table: fb
            .block_table()
            .map(|v| v.iter().collect())
            .unwrap_or_default(),
        num_cached_tokens: fb.num_cached_tokens() as usize,
        mamba_prefix_hash: if fb.has_mamba_prefix_hash() {
            Some(fb.mamba_prefix_hash())
        } else {
            None
        },
        last_token: fb.last_token(),
        block_size: fb.block_size() as usize,
        sampling_params: sp,
        pd_first_token: if fb.has_pd_first_token() {
            Some(fb.pd_first_token())
        } else {
            None
        },
        images: fb.images().map(|i| parse_image_data(&i)),
        is_tool_call_end: fb.is_tool_call_end(),
        hit_stop_sequence: fb.hit_stop_sequence(),
        stop_sequence: fb.stop_sequence().map(|s| s.to_string()),
    })
}

fn build_decode_sequence<'a>(
    fbb: &mut FlatBufferBuilder<'a>,
    ds: &RustDecodeSequence,
) -> flatbuffers::WIPOffset<schema::DecodeSequence<'a>> {
    let sp = build_sampling_params(fbb, &ds.sampling_params);
    let block_tables = fbb.create_vector(&ds.block_tables);

    schema::DecodeSequence::create(
        fbb,
        &schema::DecodeSequenceArgs {
            id: ds.id as u64,
            last_token: ds.last_token,
            len: ds.len as u64,
            last_block_tokens: ds.last_block_tokens as u64,
            block_table_last: ds.block_table_last,
            block_tables: Some(block_tables),
            sampling_params: Some(sp),
        },
    )
}

fn parse_decode_sequence(fb: &schema::DecodeSequence<'_>) -> CandleResult<RustDecodeSequence> {
    let sp = fb
        .sampling_params()
        .map(|s| parse_sampling_params(&s))
        .ok_or_else(|| fb_err("missing sampling_params in DecodeSequence"))?;

    Ok(RustDecodeSequence {
        id: fb.id() as usize,
        last_token: fb.last_token(),
        len: fb.len() as usize,
        last_block_tokens: fb.last_block_tokens() as usize,
        block_table_last: fb.block_table_last(),
        block_tables: fb
            .block_tables()
            .map(|v| v.iter().collect())
            .unwrap_or_default(),
        sampling_params: sp,
    })
}

// ---------------------------------------------------------------------------
// Helpers to finish a FlatBuffer and return the bytes (including size prefix)
// ---------------------------------------------------------------------------

fn finish_fb<'a, T: 'a>(
    fbb: &'a mut FlatBufferBuilder<'_>,
    root: flatbuffers::WIPOffset<T>,
) -> Vec<u8> {
    fbb.finish(root, None);
    fbb.finished_data().to_vec()
}

// ---------------------------------------------------------------------------
// Public API: encode / decode for MyelonRequest
// ---------------------------------------------------------------------------

pub fn encode_request(req: &MyelonRequest) -> CandleResult<Vec<u8>> {
    let mut fbb = FlatBufferBuilder::with_capacity(1024);
    match req {
        MyelonRequest::RunPrefill { sequences } => {
            let seq_offsets: Vec<_> = sequences
                .iter()
                .map(|s| build_sequence(&mut fbb, s))
                .collect();
            let seqs_vec = fbb.create_vector(&seq_offsets);
            let payload = schema::RunPrefillPayload::create(
                &mut fbb,
                &schema::RunPrefillPayloadArgs {
                    sequences: Some(seqs_vec),
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonRequest::RunDecode { sequences } => {
            let seq_offsets: Vec<_> = sequences
                .iter()
                .map(|s| build_decode_sequence(&mut fbb, s))
                .collect();
            let seqs_vec = fbb.create_vector(&seq_offsets);
            let payload = schema::RunDecodePayload::create(
                &mut fbb,
                &schema::RunDecodePayloadArgs {
                    sequences: Some(seqs_vec),
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonRequest::FinishDecode { sequence_id }
        | MyelonRequest::Cancel { sequence_id }
        | MyelonRequest::CheckPrefillStatus { sequence_id }
        | MyelonRequest::KvCacheRelease { sequence_id }
        | MyelonRequest::CheckKvCacheRelease { sequence_id } => {
            let payload = schema::SingleIdPayload::create(
                &mut fbb,
                &schema::SingleIdPayloadArgs {
                    sequence_id: *sequence_id as u64,
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonRequest::TransferPrefill { sequence }
        | MyelonRequest::KvCacheReceive { sequence } => {
            let seq_off = build_sequence(&mut fbb, sequence);
            let payload = schema::SingleSequencePayload::create(
                &mut fbb,
                &schema::SingleSequencePayloadArgs {
                    sequence: Some(seq_off),
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonRequest::ReceivePrefill { available_tokens } => {
            let payload = schema::AvailableTokensPayload::create(
                &mut fbb,
                &schema::AvailableTokensPayloadArgs {
                    available_tokens: *available_tokens as u64,
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonRequest::KvCacheSend {
            sequence,
            first_token,
        } => {
            let seq_off = build_sequence(&mut fbb, sequence);
            let payload = schema::KvCacheSendPayload::create(
                &mut fbb,
                &schema::KvCacheSendPayloadArgs {
                    sequence: Some(seq_off),
                    first_token: *first_token,
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonRequest::KvCacheSwap { mappings, swap_in } => {
            let keys: Vec<u64> = mappings.keys().map(|&k| k as u64).collect();
            let values: Vec<u64> = mappings.values().map(|&v| v as u64).collect();
            let keys_vec = fbb.create_vector(&keys);
            let values_vec = fbb.create_vector(&values);
            let payload = schema::KvCacheSwapPayload::create(
                &mut fbb,
                &schema::KvCacheSwapPayloadArgs {
                    mapping_keys: Some(keys_vec),
                    mapping_values: Some(values_vec),
                    swap_in: *swap_in,
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonRequest::Shutdown => Ok(Vec::new()),
    }
}

pub fn decode_request(kind: u8, payload: &[u8]) -> CandleResult<MyelonRequest> {
    let msg_kind = MsgKind::from_u8(kind)?;
    match msg_kind {
        MsgKind::RunPrefill => {
            let fb = flatbuffers::root::<schema::RunPrefillPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let seqs = fb
                .sequences()
                .ok_or_else(|| fb_err("missing sequences in RunPrefillPayload"))?;
            let sequences: CandleResult<Vec<RustSequence>> =
                (0..seqs.len()).map(|i| parse_sequence(&seqs.get(i))).collect();
            Ok(MyelonRequest::RunPrefill {
                sequences: sequences?,
            })
        }
        MsgKind::RunDecode => {
            let fb = flatbuffers::root::<schema::RunDecodePayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let seqs = fb
                .sequences()
                .ok_or_else(|| fb_err("missing sequences in RunDecodePayload"))?;
            let sequences: CandleResult<Vec<RustDecodeSequence>> = (0..seqs.len())
                .map(|i| parse_decode_sequence(&seqs.get(i)))
                .collect();
            Ok(MyelonRequest::RunDecode {
                sequences: sequences?,
            })
        }
        MsgKind::FinishDecode => {
            let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonRequest::FinishDecode {
                sequence_id: fb.sequence_id() as usize,
            })
        }
        MsgKind::Cancel => {
            let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonRequest::Cancel {
                sequence_id: fb.sequence_id() as usize,
            })
        }
        MsgKind::TransferPrefill => {
            let fb = flatbuffers::root::<schema::SingleSequencePayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let seq = fb
                .sequence()
                .ok_or_else(|| fb_err("missing sequence in TransferPrefill"))?;
            Ok(MyelonRequest::TransferPrefill {
                sequence: parse_sequence(&seq)?,
            })
        }
        MsgKind::ReceivePrefill => {
            let fb = flatbuffers::root::<schema::AvailableTokensPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonRequest::ReceivePrefill {
                available_tokens: fb.available_tokens() as usize,
            })
        }
        MsgKind::CheckPrefillStatus => {
            let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonRequest::CheckPrefillStatus {
                sequence_id: fb.sequence_id() as usize,
            })
        }
        MsgKind::KvCacheSend => {
            let fb = flatbuffers::root::<schema::KvCacheSendPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let seq = fb
                .sequence()
                .ok_or_else(|| fb_err("missing sequence in KvCacheSend"))?;
            Ok(MyelonRequest::KvCacheSend {
                sequence: parse_sequence(&seq)?,
                first_token: fb.first_token(),
            })
        }
        MsgKind::KvCacheReceive => {
            let fb = flatbuffers::root::<schema::SingleSequencePayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let seq = fb
                .sequence()
                .ok_or_else(|| fb_err("missing sequence in KvCacheReceive"))?;
            Ok(MyelonRequest::KvCacheReceive {
                sequence: parse_sequence(&seq)?,
            })
        }
        MsgKind::KvCacheRelease => {
            let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonRequest::KvCacheRelease {
                sequence_id: fb.sequence_id() as usize,
            })
        }
        MsgKind::CheckKvCacheRelease => {
            let fb = flatbuffers::root::<schema::SingleIdPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonRequest::CheckKvCacheRelease {
                sequence_id: fb.sequence_id() as usize,
            })
        }
        MsgKind::KvCacheSwap => {
            let fb = flatbuffers::root::<schema::KvCacheSwapPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let keys = fb
                .mapping_keys()
                .map(|v| v.iter().map(|x| x as usize).collect::<Vec<_>>())
                .unwrap_or_default();
            let values = fb
                .mapping_values()
                .map(|v| v.iter().map(|x| x as usize).collect::<Vec<_>>())
                .unwrap_or_default();
            let mappings: HashMap<usize, usize> = keys.into_iter().zip(values).collect();
            Ok(MyelonRequest::KvCacheSwap {
                mappings,
                swap_in: fb.swap_in(),
            })
        }
        MsgKind::Shutdown => {
            if !payload.is_empty() {
                candle_core::bail!("Shutdown request must not carry a payload");
            }
            Ok(MyelonRequest::Shutdown)
        }
        _ => {
            candle_core::bail!("response kind {} is not a request", kind);
        }
    }
}

// ---------------------------------------------------------------------------
// Public API: encode / decode for MyelonResponse
// ---------------------------------------------------------------------------

pub fn encode_response(resp: &MyelonResponse) -> CandleResult<Vec<u8>> {
    let mut fbb = FlatBufferBuilder::with_capacity(512);
    match resp {
        MyelonResponse::RunResponse(output_ids) => {
            let ids = fbb.create_vector(output_ids);
            let payload = schema::RunResponsePayload::create(
                &mut fbb,
                &schema::RunResponsePayloadArgs {
                    output_ids: Some(ids),
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonResponse::TransferPrefillResponse(v)
        | MyelonResponse::CheckPrefillStatusResponse(v)
        | MyelonResponse::KvCacheSendResponse(v)
        | MyelonResponse::KvCacheReleaseResponse(v)
        | MyelonResponse::CheckKvCacheReleaseResponse(v)
        | MyelonResponse::KvCacheSwapResponse(v) => {
            let payload = schema::BoolPayload::create(
                &mut fbb,
                &schema::BoolPayloadArgs { value: *v },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonResponse::ReceivePrefillResponse((success, seq_opt)) => {
            let seq_off = seq_opt.as_ref().map(|s| build_sequence(&mut fbb, s));
            let payload = schema::ReceivePrefillResponsePayload::create(
                &mut fbb,
                &schema::ReceivePrefillResponsePayloadArgs {
                    success: *success,
                    sequence: seq_off,
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonResponse::KvCacheReceiveResponse((success, first_token, num_tokens)) => {
            let payload = schema::KvCacheReceiveResponsePayload::create(
                &mut fbb,
                &schema::KvCacheReceiveResponsePayloadArgs {
                    success: *success,
                    first_token: *first_token,
                    num_tokens: *num_tokens as u64,
                },
            );
            Ok(finish_fb(&mut fbb, payload))
        }
        MyelonResponse::Error(error) => Ok(error.as_bytes().to_vec()),
    }
}

pub fn decode_response(kind: u8, payload: &[u8]) -> CandleResult<MyelonResponse> {
    match MsgKind::from_u8(kind)? {
        MsgKind::RunResponse => {
            let fb = flatbuffers::root::<schema::RunResponsePayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let ids = fb
                .output_ids()
                .map(|v| v.iter().collect())
                .unwrap_or_default();
            Ok(MyelonResponse::RunResponse(ids))
        }
        MsgKind::TransferPrefillResponse => {
            let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonResponse::TransferPrefillResponse(fb.value()))
        }
        MsgKind::ReceivePrefillResponse => {
            let fb = flatbuffers::root::<schema::ReceivePrefillResponsePayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            let seq = fb.sequence().map(|s| parse_sequence(&s)).transpose()?;
            Ok(MyelonResponse::ReceivePrefillResponse((
                fb.success(),
                seq,
            )))
        }
        MsgKind::CheckPrefillStatusResponse => {
            let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonResponse::CheckPrefillStatusResponse(fb.value()))
        }
        MsgKind::KvCacheSendResponse => {
            let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonResponse::KvCacheSendResponse(fb.value()))
        }
        MsgKind::KvCacheReceiveResponse => {
            let fb = flatbuffers::root::<schema::KvCacheReceiveResponsePayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonResponse::KvCacheReceiveResponse((
                fb.success(),
                fb.first_token(),
                fb.num_tokens() as usize,
            )))
        }
        MsgKind::KvCacheReleaseResponse => {
            let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonResponse::KvCacheReleaseResponse(fb.value()))
        }
        MsgKind::CheckKvCacheReleaseResponse => {
            let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonResponse::CheckKvCacheReleaseResponse(fb.value()))
        }
        MsgKind::KvCacheSwapResponse => {
            let fb = flatbuffers::root::<schema::BoolPayload>(payload)
                .map_err(|e| fb_err(&e.to_string()))?;
            Ok(MyelonResponse::KvCacheSwapResponse(fb.value()))
        }
        MsgKind::Error => Ok(MyelonResponse::Error(
            String::from_utf8_lossy(payload).into_owned(),
        )),
        _ => {
            candle_core::bail!("request kind {} is not a response", kind);
        }
    }
}
