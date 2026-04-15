//! rkyv round-trip tests for Myelon IPC wire types.
//! Run with: cargo test --test rkyv_roundtrip --features metal,myelon-rkyv
#![cfg(feature = "codec-rkyv")]

use vllm_rs::core::sequence::{DecodeSequence, Sequence, SequenceStatus};
use vllm_rs::utils::config::SamplingParams;
use vllm_rs::utils::image::ImageData;

fn make_test_sampling_params() -> SamplingParams {
    SamplingParams {
        temperature: Some(0.7),
        max_tokens: Some(256),
        ignore_eos: false,
        top_k: Some(50),
        top_p: Some(0.9),
        session_id: Some("test-session".to_string()),
        frequency_penalty: Some(0.0),
        presence_penalty: Some(0.0),
        stop_sequences: Some(vec!["<|endoftext|>".to_string()]),
        stop_token_ids: None,
        thinking: Some(false),
        mcp_mode: None,
        grammar: None,
        grammar_json: Some("{\"type\": \"json\"}".to_string()),
        reasoning_effort: None,
    }
}

fn make_test_sequence(id: usize) -> Sequence {
    Sequence {
        id,
        created_time: 1000,
        swapped_time: None,
        status: SequenceStatus::Running,
        token_ids: vec![1, 2, 3, 4, 5, 100, 200, 300],
        output_ids: vec![10, 20, 30],
        block_table: vec![0, 1, 2],
        num_cached_tokens: 0,
        mamba_prefix_hash: None,
        last_token: 30,
        block_size: 16,
        sampling_params: make_test_sampling_params(),
        pd_first_token: None,
        images: None,
        is_tool_call_end: false,
        hit_stop_sequence: false,
        stop_sequence: None,
    }
}

#[test]
fn test_sequence_rkyv_roundtrip() {
    let seq = make_test_sequence(42);
    let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&seq).expect("rkyv serialize");

    // Full deserialization round-trip
    let archived =
        rkyv::access::<rkyv::Archived<Sequence>, rkyv::rancor::Error>(&bytes).expect("access");
    let deserialized: Sequence =
        rkyv::deserialize::<Sequence, rkyv::rancor::Error>(archived).expect("deserialize");
    assert_eq!(deserialized.id, 42);
    assert_eq!(deserialized.last_token, 30);
    assert_eq!(deserialized.token_ids, vec![1, 2, 3, 4, 5, 100, 200, 300]);
    assert_eq!(deserialized.output_ids, vec![10, 20, 30]);
    assert_eq!(deserialized.block_table, vec![0, 1, 2]);
    assert_eq!(deserialized.status, SequenceStatus::Running);
    assert_eq!(deserialized.sampling_params.temperature, Some(0.7));
    assert_eq!(deserialized.sampling_params.max_tokens, Some(256));
    assert_eq!(
        deserialized.sampling_params.grammar_json,
        Some("{\"type\": \"json\"}".to_string())
    );
}

#[test]
fn test_decode_sequence_rkyv_roundtrip() {
    let seq = make_test_sequence(99);
    let decode_seq = DecodeSequence::new(&seq);
    let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&decode_seq).expect("serialize");
    let archived =
        rkyv::access::<rkyv::Archived<DecodeSequence>, rkyv::rancor::Error>(&bytes)
            .expect("access");
    let deserialized: DecodeSequence =
        rkyv::deserialize::<DecodeSequence, rkyv::rancor::Error>(archived).expect("deserialize");
    assert_eq!(deserialized.id, 99);
    assert_eq!(deserialized.last_token, 30);
    assert_eq!(deserialized.sampling_params.top_k, Some(50));
}

#[test]
fn test_sequence_vec_rkyv_roundtrip_256() {
    let sequences: Vec<Sequence> = (0..256).map(|i| make_test_sequence(i)).collect();
    let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&sequences).expect("serialize vec");

    // Zero-copy access
    let archived =
        rkyv::access::<rkyv::Archived<Vec<Sequence>>, rkyv::rancor::Error>(&bytes)
            .expect("access vec");
    assert_eq!(archived.len(), 256);

    // Spot-check fields without deserializing
    for (i, a) in archived.iter().enumerate() {
        assert_eq!(a.token_ids.len(), 8);
        assert_eq!(a.output_ids.len(), 3);
        // usize comparison: archived usize may differ from native on some platforms
        let deserialized: Sequence =
            rkyv::deserialize::<Sequence, rkyv::rancor::Error>(a).expect("deserialize");
        assert_eq!(deserialized.id, i);
    }
}

#[test]
fn test_image_data_rkyv_roundtrip() {
    let img = ImageData {
        raw: vec![0u8; 1024],
        shape: vec![1, 3, 224, 224],
        patches: vec![(0, 224), (224, 448)],
        image_idx: 0,
        image_token_offset: 5,
        tokens_per_image: vec![576],
        image_token_id: Some(151655),
    };
    let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&img).expect("serialize");
    let archived =
        rkyv::access::<rkyv::Archived<ImageData>, rkyv::rancor::Error>(&bytes).expect("access");
    let deserialized: ImageData =
        rkyv::deserialize::<ImageData, rkyv::rancor::Error>(archived).expect("deserialize");
    assert_eq!(deserialized.raw.len(), 1024);
    assert_eq!(deserialized.shape, vec![1, 3, 224, 224]);
    assert_eq!(deserialized.image_token_id, Some(151655));
}

#[test]
fn test_sequence_with_images_rkyv_roundtrip() {
    let mut seq = make_test_sequence(7);
    seq.images = Some(ImageData {
        raw: vec![128u8; 512],
        shape: vec![1, 3, 64, 64],
        patches: vec![(0, 64)],
        image_idx: 0,
        image_token_offset: 0,
        tokens_per_image: vec![256],
        image_token_id: None,
    });
    let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&seq).expect("serialize");
    let archived =
        rkyv::access::<rkyv::Archived<Sequence>, rkyv::rancor::Error>(&bytes).expect("access");
    let deserialized: Sequence =
        rkyv::deserialize::<Sequence, rkyv::rancor::Error>(archived).expect("deserialize");
    assert!(deserialized.images.is_some());
    assert_eq!(deserialized.images.unwrap().raw.len(), 512);
}
