//! Tests that all MyelonRequest and MyelonResponse variants round-trip
//! through the rkyv codec (encode → decode).
//! Run with: cargo test --test rkyv_codec_roundtrip --features metal,myelon-rkyv
#![cfg(feature = "myelon-rkyv")]

use std::collections::HashMap;
use vllm_rs::core::sequence::{DecodeSequence, Sequence, SequenceStatus};
use vllm_rs::ipc::myelon_ipc::{MsgKind, MyelonRequest, MyelonResponse};
use vllm_rs::ipc::rkyv_codec;
use vllm_rs::utils::config::SamplingParams;

fn make_sampling_params() -> SamplingParams {
    SamplingParams {
        temperature: Some(0.7),
        max_tokens: Some(256),
        ignore_eos: false,
        top_k: Some(50),
        top_p: Some(0.9),
        session_id: None,
        frequency_penalty: None,
        presence_penalty: None,
        stop_sequences: None,
        stop_token_ids: None,
        thinking: None,
        mcp_mode: None,
        grammar: None,
        grammar_json: None,
        reasoning_effort: None,
    }
}

fn make_sequence(id: usize) -> Sequence {
    Sequence {
        id,
        created_time: 1000,
        swapped_time: None,
        status: SequenceStatus::Running,
        token_ids: vec![1, 2, 3, 4, 5],
        output_ids: vec![10, 20],
        block_table: vec![0, 1],
        num_cached_tokens: 0,
        mamba_prefix_hash: None,
        last_token: 20,
        block_size: 16,
        sampling_params: make_sampling_params(),
        pd_first_token: None,
        images: None,
        is_tool_call_end: false,
        hit_stop_sequence: false,
        stop_sequence: None,
    }
}

fn roundtrip_request(req: &MyelonRequest) -> MyelonRequest {
    let kind = req.kind() as u8;
    let bytes = rkyv_codec::encode_request(req).expect("encode");
    rkyv_codec::decode_request(kind, &bytes).expect("decode")
}

fn roundtrip_response(resp: &MyelonResponse) -> MyelonResponse {
    let kind = resp.kind() as u8;
    let bytes = rkyv_codec::encode_response(resp).expect("encode");
    rkyv_codec::decode_response(kind, &bytes).expect("decode")
}

// === Request round-trip tests ===

#[test]
fn test_run_prefill() {
    let seqs: Vec<Sequence> = (0..8).map(make_sequence).collect();
    let req = MyelonRequest::RunPrefill {
        sequences: seqs.clone(),
    };
    if let MyelonRequest::RunPrefill { sequences } = roundtrip_request(&req) {
        assert_eq!(sequences.len(), 8);
        assert_eq!(sequences[0].id, 0);
        assert_eq!(sequences[7].id, 7);
        assert_eq!(sequences[3].token_ids, vec![1, 2, 3, 4, 5]);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_run_decode() {
    let seq = make_sequence(42);
    let decode_seq = DecodeSequence::new(&seq);
    let req = MyelonRequest::RunDecode {
        sequences: vec![decode_seq],
    };
    if let MyelonRequest::RunDecode { sequences } = roundtrip_request(&req) {
        assert_eq!(sequences.len(), 1);
        assert_eq!(sequences[0].id, 42);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_finish_decode() {
    let req = MyelonRequest::FinishDecode { sequence_id: 99 };
    if let MyelonRequest::FinishDecode { sequence_id } = roundtrip_request(&req) {
        assert_eq!(sequence_id, 99);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_cancel() {
    let req = MyelonRequest::Cancel { sequence_id: 55 };
    if let MyelonRequest::Cancel { sequence_id } = roundtrip_request(&req) {
        assert_eq!(sequence_id, 55);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_transfer_prefill() {
    let req = MyelonRequest::TransferPrefill {
        sequence: make_sequence(77),
    };
    if let MyelonRequest::TransferPrefill { sequence } = roundtrip_request(&req) {
        assert_eq!(sequence.id, 77);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_receive_prefill() {
    let req = MyelonRequest::ReceivePrefill {
        available_tokens: 1024,
    };
    if let MyelonRequest::ReceivePrefill { available_tokens } = roundtrip_request(&req) {
        assert_eq!(available_tokens, 1024);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_check_prefill_status() {
    let req = MyelonRequest::CheckPrefillStatus { sequence_id: 33 };
    if let MyelonRequest::CheckPrefillStatus { sequence_id } = roundtrip_request(&req) {
        assert_eq!(sequence_id, 33);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_send() {
    let req = MyelonRequest::KvCacheSend {
        sequence: make_sequence(11),
        first_token: 42,
    };
    if let MyelonRequest::KvCacheSend {
        sequence,
        first_token,
    } = roundtrip_request(&req)
    {
        assert_eq!(sequence.id, 11);
        assert_eq!(first_token, 42);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_receive() {
    let req = MyelonRequest::KvCacheReceive {
        sequence: make_sequence(22),
    };
    if let MyelonRequest::KvCacheReceive { sequence } = roundtrip_request(&req) {
        assert_eq!(sequence.id, 22);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_release() {
    let req = MyelonRequest::KvCacheRelease { sequence_id: 88 };
    if let MyelonRequest::KvCacheRelease { sequence_id } = roundtrip_request(&req) {
        assert_eq!(sequence_id, 88);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_check_kv_cache_release() {
    let req = MyelonRequest::CheckKvCacheRelease { sequence_id: 44 };
    if let MyelonRequest::CheckKvCacheRelease { sequence_id } = roundtrip_request(&req) {
        assert_eq!(sequence_id, 44);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_swap() {
    let mut mappings = HashMap::new();
    mappings.insert(0, 10);
    mappings.insert(1, 11);
    mappings.insert(2, 12);
    let req = MyelonRequest::KvCacheSwap {
        mappings: mappings.clone(),
        swap_in: true,
    };
    if let MyelonRequest::KvCacheSwap {
        mappings: m,
        swap_in,
    } = roundtrip_request(&req)
    {
        assert_eq!(m.len(), 3);
        assert_eq!(m[&0], 10);
        assert_eq!(m[&1], 11);
        assert_eq!(m[&2], 12);
        assert!(swap_in);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_shutdown() {
    let req = MyelonRequest::Shutdown;
    if let MyelonRequest::Shutdown = roundtrip_request(&req) {
        // ok
    } else {
        panic!("wrong variant");
    }
}

// === Response round-trip tests ===

#[test]
fn test_run_response() {
    let resp = MyelonResponse::RunResponse(vec![1, 2, 3, 4, 5]);
    if let MyelonResponse::RunResponse(ids) = roundtrip_response(&resp) {
        assert_eq!(ids, vec![1, 2, 3, 4, 5]);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_transfer_prefill_response() {
    let resp = MyelonResponse::TransferPrefillResponse(true);
    if let MyelonResponse::TransferPrefillResponse(v) = roundtrip_response(&resp) {
        assert!(v);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_receive_prefill_response() {
    let resp = MyelonResponse::ReceivePrefillResponse((true, Some(make_sequence(5))));
    if let MyelonResponse::ReceivePrefillResponse((success, seq)) = roundtrip_response(&resp) {
        assert!(success);
        assert_eq!(seq.unwrap().id, 5);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_check_prefill_status_response() {
    let resp = MyelonResponse::CheckPrefillStatusResponse(false);
    if let MyelonResponse::CheckPrefillStatusResponse(v) = roundtrip_response(&resp) {
        assert!(!v);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_send_response() {
    let resp = MyelonResponse::KvCacheSendResponse(true);
    if let MyelonResponse::KvCacheSendResponse(v) = roundtrip_response(&resp) {
        assert!(v);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_receive_response() {
    let resp = MyelonResponse::KvCacheReceiveResponse((true, 42, 1024));
    if let MyelonResponse::KvCacheReceiveResponse((success, token, count)) =
        roundtrip_response(&resp)
    {
        assert!(success);
        assert_eq!(token, 42);
        assert_eq!(count, 1024);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_release_response() {
    let resp = MyelonResponse::KvCacheReleaseResponse(true);
    if let MyelonResponse::KvCacheReleaseResponse(v) = roundtrip_response(&resp) {
        assert!(v);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_check_kv_cache_release_response() {
    let resp = MyelonResponse::CheckKvCacheReleaseResponse(false);
    if let MyelonResponse::CheckKvCacheReleaseResponse(v) = roundtrip_response(&resp) {
        assert!(!v);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_kv_cache_swap_response() {
    let resp = MyelonResponse::KvCacheSwapResponse(true);
    if let MyelonResponse::KvCacheSwapResponse(v) = roundtrip_response(&resp) {
        assert!(v);
    } else {
        panic!("wrong variant");
    }
}

#[test]
fn test_error_response() {
    let resp = MyelonResponse::Error("something broke".to_string());
    if let MyelonResponse::Error(msg) = roundtrip_response(&resp) {
        assert_eq!(msg, "something broke");
    } else {
        panic!("wrong variant");
    }
}
