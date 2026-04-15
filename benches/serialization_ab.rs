//! A/B benchmark: bincode vs rkyv vs FlatBuffers for Myelon IPC serialization.
//!
//! Run all three:
//!   cargo bench --bench serialization_ab --features metal,myelon-rkyv,myelon-flatbuf
//!
//! Run rkyv only:
//!   cargo bench --bench serialization_ab --features metal,myelon-rkyv
//!
//! Run flatbuf only:
//!   cargo bench --bench serialization_ab --features metal,myelon-flatbuf

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion};

use vllm_rs::core::sequence::{DecodeSequence, Sequence, SequenceStatus};
use vllm_rs::utils::config::SamplingParams;

// ---------- test data generators ----------

fn make_sampling_params() -> SamplingParams {
    SamplingParams {
        temperature: Some(0.7),
        max_tokens: Some(256),
        ignore_eos: false,
        top_k: Some(50),
        top_p: Some(0.9),
        session_id: Some("bench-session".to_string()),
        frequency_penalty: Some(0.1),
        presence_penalty: Some(0.1),
        stop_sequences: Some(vec!["<|endoftext|>".to_string()]),
        stop_token_ids: None,
        thinking: None,
        mcp_mode: None,
        grammar: None,
        grammar_json: None,
        reasoning_effort: None,
    }
}

fn make_sequence(id: usize) -> Sequence {
    // Realistic sizes: ~128 token_ids, ~32 output_ids, ~8 blocks
    Sequence {
        id,
        created_time: 1713200000 + id,
        swapped_time: None,
        status: SequenceStatus::Running,
        token_ids: (0..128).map(|i| (i * 31 + id as u32) % 151000).collect(),
        output_ids: (0..32).map(|i| (i * 17 + id as u32) % 151000).collect(),
        block_table: (0..8).map(|i| i as u32 + id as u32 * 8).collect(),
        num_cached_tokens: 64,
        mamba_prefix_hash: None,
        last_token: 42,
        block_size: 16,
        sampling_params: make_sampling_params(),
        pd_first_token: None,
        images: None,
        is_tool_call_end: false,
        hit_stop_sequence: false,
        stop_sequence: None,
    }
}

fn make_sequences(n: usize) -> Vec<Sequence> {
    (0..n).map(make_sequence).collect()
}

fn make_decode_sequences(n: usize) -> Vec<DecodeSequence> {
    make_sequences(n)
        .iter()
        .map(|s| DecodeSequence::new(s))
        .collect()
}

fn make_output_ids(n: usize) -> Vec<u32> {
    (0..n).map(|i| (i as u32 * 37) % 151000).collect()
}

// ---------- bincode baseline ----------

fn bincode_encode_prefill(sequences: &[Sequence]) -> Vec<u8> {
    bincode::serialize(&(sequences, true)).unwrap()
}

fn bincode_decode_prefill(bytes: &[u8]) -> Vec<Sequence> {
    let (seqs, _): (Vec<Sequence>, bool) = bincode::deserialize(bytes).unwrap();
    seqs
}

fn bincode_encode_decode(sequences: &[DecodeSequence]) -> Vec<u8> {
    bincode::serialize(&(sequences, false)).unwrap()
}

fn bincode_decode_decode(bytes: &[u8]) -> Vec<DecodeSequence> {
    let (seqs, _): (Vec<DecodeSequence>, bool) = bincode::deserialize(bytes).unwrap();
    seqs
}

fn bincode_encode_response(ids: &[u32]) -> Vec<u8> {
    // Current vllm.rs uses custom u32 slice encoding, not bincode
    let mut buf = Vec::with_capacity(4 + ids.len() * 4);
    buf.extend_from_slice(&(ids.len() as u32).to_le_bytes());
    for &id in ids {
        buf.extend_from_slice(&id.to_le_bytes());
    }
    buf
}

fn bincode_decode_response(bytes: &[u8]) -> Vec<u32> {
    let count = u32::from_le_bytes(bytes[0..4].try_into().unwrap()) as usize;
    let mut ids = Vec::with_capacity(count);
    for i in 0..count {
        let offset = 4 + i * 4;
        ids.push(u32::from_le_bytes(
            bytes[offset..offset + 4].try_into().unwrap(),
        ));
    }
    ids
}

// ---------- benchmarks ----------

fn bench_encode_run_prefill(c: &mut Criterion) {
    let mut group = c.benchmark_group("encode_RunPrefill");
    for n in [8, 64, 256] {
        let sequences = make_sequences(n);

        group.bench_with_input(BenchmarkId::new("bincode", n), &sequences, |b, seqs| {
            b.iter(|| black_box(bincode_encode_prefill(seqs)))
        });

        #[cfg(feature = "myelon-rkyv")]
        group.bench_with_input(BenchmarkId::new("rkyv", n), &sequences, |b, seqs| {
            b.iter(|| {
                black_box(
                    rkyv::to_bytes::<rkyv::rancor::Error>(seqs)
                        .unwrap()
                        .to_vec(),
                )
            })
        });

        #[cfg(feature = "myelon-flatbuf")]
        group.bench_with_input(BenchmarkId::new("flatbuf", n), &sequences, |b, seqs| {
            b.iter(|| {
                let req = vllm_rs::ipc::myelon_ipc::MyelonRequest::RunPrefill {
                    sequences: seqs.clone(),
                };
                black_box(vllm_rs::ipc::flatbuf_codec::encode_request(&req).unwrap())
            })
        });
    }
    group.finish();
}

fn bench_decode_run_prefill(c: &mut Criterion) {
    let mut group = c.benchmark_group("decode_RunPrefill");
    for n in [8, 64, 256] {
        let sequences = make_sequences(n);
        let bincode_bytes = bincode_encode_prefill(&sequences);

        group.bench_with_input(
            BenchmarkId::new("bincode", n),
            &bincode_bytes,
            |b, bytes| b.iter(|| black_box(bincode_decode_prefill(bytes))),
        );

        #[cfg(feature = "myelon-rkyv")]
        {
            let rkyv_bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&sequences)
                .unwrap()
                .to_vec();
            group.bench_with_input(
                BenchmarkId::new("rkyv_zero_copy", n),
                &rkyv_bytes,
                |b, bytes| {
                    b.iter(|| {
                        let archived = rkyv::access::<
                            rkyv::Archived<Vec<Sequence>>,
                            rkyv::rancor::Error,
                        >(bytes)
                        .unwrap();
                        // Access fields without allocation — the real zero-copy win
                        for seq in archived.iter() {
                            black_box(seq.token_ids.len());
                            black_box(seq.output_ids.len());
                            black_box(seq.block_table.len());
                        }
                    })
                },
            );
            group.bench_with_input(
                BenchmarkId::new("rkyv_owned", n),
                &rkyv_bytes,
                |b, bytes| {
                    b.iter(|| {
                        let archived = rkyv::access::<
                            rkyv::Archived<Vec<Sequence>>,
                            rkyv::rancor::Error,
                        >(bytes)
                        .unwrap();
                        let owned: Vec<Sequence> =
                            rkyv::deserialize::<Vec<Sequence>, rkyv::rancor::Error>(archived)
                                .unwrap();
                        black_box(owned);
                    })
                },
            );
        }

        #[cfg(feature = "myelon-flatbuf")]
        {
            let req = vllm_rs::ipc::myelon_ipc::MyelonRequest::RunPrefill {
                sequences: sequences.clone(),
            };
            let fb_bytes = vllm_rs::ipc::flatbuf_codec::encode_request(&req).unwrap();
            group.bench_with_input(
                BenchmarkId::new("flatbuf", n),
                &fb_bytes,
                |b, bytes| {
                    b.iter(|| {
                        black_box(
                            vllm_rs::ipc::flatbuf_codec::decode_request(1, bytes).unwrap(),
                        )
                    })
                },
            );
        }
    }
    group.finish();
}

fn bench_encode_run_decode(c: &mut Criterion) {
    let mut group = c.benchmark_group("encode_RunDecode");
    for n in [8, 64, 256] {
        let sequences = make_decode_sequences(n);

        group.bench_with_input(BenchmarkId::new("bincode", n), &sequences, |b, seqs| {
            b.iter(|| black_box(bincode_encode_decode(seqs)))
        });

        #[cfg(feature = "myelon-rkyv")]
        group.bench_with_input(BenchmarkId::new("rkyv", n), &sequences, |b, seqs| {
            b.iter(|| {
                black_box(
                    rkyv::to_bytes::<rkyv::rancor::Error>(seqs)
                        .unwrap()
                        .to_vec(),
                )
            })
        });

        #[cfg(feature = "myelon-flatbuf")]
        group.bench_with_input(BenchmarkId::new("flatbuf", n), &sequences, |b, seqs| {
            b.iter(|| {
                let req = vllm_rs::ipc::myelon_ipc::MyelonRequest::RunDecode {
                    sequences: seqs.clone(),
                };
                black_box(vllm_rs::ipc::flatbuf_codec::encode_request(&req).unwrap())
            })
        });
    }
    group.finish();
}

fn bench_decode_run_decode(c: &mut Criterion) {
    let mut group = c.benchmark_group("decode_RunDecode");
    for n in [8, 64, 256] {
        let sequences = make_decode_sequences(n);
        let bincode_bytes = bincode_encode_decode(&sequences);

        group.bench_with_input(
            BenchmarkId::new("bincode", n),
            &bincode_bytes,
            |b, bytes| b.iter(|| black_box(bincode_decode_decode(bytes))),
        );

        #[cfg(feature = "myelon-rkyv")]
        {
            let rkyv_bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&sequences)
                .unwrap()
                .to_vec();
            group.bench_with_input(
                BenchmarkId::new("rkyv_zero_copy", n),
                &rkyv_bytes,
                |b, bytes| {
                    b.iter(|| {
                        let archived = rkyv::access::<
                            rkyv::Archived<Vec<DecodeSequence>>,
                            rkyv::rancor::Error,
                        >(bytes)
                        .unwrap();
                        for seq in archived.iter() {
                            black_box(seq.block_tables.len());
                        }
                    })
                },
            );
        }

        #[cfg(feature = "myelon-flatbuf")]
        {
            let req = vllm_rs::ipc::myelon_ipc::MyelonRequest::RunDecode {
                sequences: sequences.clone(),
            };
            let fb_bytes = vllm_rs::ipc::flatbuf_codec::encode_request(&req).unwrap();
            group.bench_with_input(
                BenchmarkId::new("flatbuf", n),
                &fb_bytes,
                |b, bytes| {
                    b.iter(|| {
                        black_box(
                            vllm_rs::ipc::flatbuf_codec::decode_request(2, bytes).unwrap(),
                        )
                    })
                },
            );
        }
    }
    group.finish();
}

fn bench_encode_run_response(c: &mut Criterion) {
    let mut group = c.benchmark_group("encode_RunResponse");
    for n in [32, 256, 1024] {
        let ids = make_output_ids(n);

        group.bench_with_input(BenchmarkId::new("custom_u32", n), &ids, |b, ids| {
            b.iter(|| black_box(bincode_encode_response(ids)))
        });

        #[cfg(feature = "myelon-rkyv")]
        group.bench_with_input(BenchmarkId::new("rkyv", n), &ids, |b, ids| {
            b.iter(|| {
                black_box(
                    rkyv::to_bytes::<rkyv::rancor::Error>(ids)
                        .unwrap()
                        .to_vec(),
                )
            })
        });

        #[cfg(feature = "myelon-flatbuf")]
        group.bench_with_input(BenchmarkId::new("flatbuf", n), &ids, |b, ids| {
            b.iter(|| {
                let resp = vllm_rs::ipc::myelon_ipc::MyelonResponse::RunResponse(ids.clone());
                black_box(vllm_rs::ipc::flatbuf_codec::encode_response(&resp).unwrap())
            })
        });
    }
    group.finish();
}

fn bench_decode_run_response(c: &mut Criterion) {
    let mut group = c.benchmark_group("decode_RunResponse");
    for n in [32, 256, 1024] {
        let ids = make_output_ids(n);
        let custom_bytes = bincode_encode_response(&ids);

        group.bench_with_input(
            BenchmarkId::new("custom_u32", n),
            &custom_bytes,
            |b, bytes| b.iter(|| black_box(bincode_decode_response(bytes))),
        );

        #[cfg(feature = "myelon-rkyv")]
        {
            let rkyv_bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&ids).unwrap().to_vec();
            group.bench_with_input(
                BenchmarkId::new("rkyv_zero_copy", n),
                &rkyv_bytes,
                |b, bytes| {
                    b.iter(|| {
                        let archived =
                            rkyv::access::<rkyv::Archived<Vec<u32>>, rkyv::rancor::Error>(bytes)
                                .unwrap();
                        black_box(archived.len());
                    })
                },
            );
        }

        #[cfg(feature = "myelon-flatbuf")]
        {
            let resp = vllm_rs::ipc::myelon_ipc::MyelonResponse::RunResponse(ids.clone());
            let fb_bytes = vllm_rs::ipc::flatbuf_codec::encode_response(&resp).unwrap();
            group.bench_with_input(
                BenchmarkId::new("flatbuf", n),
                &fb_bytes,
                |b, bytes| {
                    b.iter(|| {
                        black_box(
                            vllm_rs::ipc::flatbuf_codec::decode_response(100, bytes).unwrap(),
                        )
                    })
                },
            );
        }
    }
    group.finish();
}

fn bench_payload_sizes(c: &mut Criterion) {
    let mut group = c.benchmark_group("payload_size_bytes");
    // Not a timing bench — just measure payload sizes once
    let sequences = make_sequences(256);
    let decode_sequences = make_decode_sequences(256);
    let output_ids = make_output_ids(256);

    // RunPrefill 256
    let bc = bincode_encode_prefill(&sequences);
    println!("RunPrefill/256 bincode: {} bytes", bc.len());

    #[cfg(feature = "myelon-rkyv")]
    {
        let rk = rkyv::to_bytes::<rkyv::rancor::Error>(&sequences)
            .unwrap()
            .to_vec();
        println!("RunPrefill/256 rkyv: {} bytes", rk.len());
    }

    #[cfg(feature = "myelon-flatbuf")]
    {
        let req = vllm_rs::ipc::myelon_ipc::MyelonRequest::RunPrefill {
            sequences: sequences.clone(),
        };
        let fb = vllm_rs::ipc::flatbuf_codec::encode_request(&req).unwrap();
        println!("RunPrefill/256 flatbuf: {} bytes", fb.len());
    }

    // RunDecode 256
    let bc = bincode_encode_decode(&decode_sequences);
    println!("RunDecode/256 bincode: {} bytes", bc.len());

    // RunResponse 256
    let bc = bincode_encode_response(&output_ids);
    println!("RunResponse/256 custom_u32: {} bytes", bc.len());

    // Dummy bench to satisfy Criterion
    group.bench_function("noop", |b| b.iter(|| black_box(1 + 1)));
    group.finish();
}

criterion_group!(
    benches,
    bench_encode_run_prefill,
    bench_decode_run_prefill,
    bench_encode_run_decode,
    bench_decode_run_decode,
    bench_encode_run_response,
    bench_decode_run_response,
    bench_payload_sizes,
);
criterion_main!(benches);
