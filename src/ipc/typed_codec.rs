use crate::ipc::myelon_ipc::{MyelonRequest, MyelonResponse};
use myelon_playground::{Codec, CodecError};

pub const MYELON_TYPED_ENVELOPE_HEADER_BYTES: usize = 16;

#[derive(Debug, Clone)]
pub struct TypedMyelonRequest(pub MyelonRequest);

impl TypedMyelonRequest {
    pub fn into_inner(self) -> MyelonRequest {
        self.0
    }
}

#[derive(Debug, Clone)]
pub struct TypedMyelonResponse(pub MyelonResponse);

impl TypedMyelonResponse {
    pub fn into_inner(self) -> MyelonResponse {
        self.0
    }
}

fn encode_envelope(tag: u8, payload: &[u8]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(MYELON_TYPED_ENVELOPE_HEADER_BYTES + payload.len());
    bytes.push(tag);
    bytes.resize(MYELON_TYPED_ENVELOPE_HEADER_BYTES, 0);
    bytes.extend_from_slice(payload);
    bytes
}

fn decode_envelope(bytes: &[u8]) -> Result<(u8, &[u8]), CodecError> {
    if bytes.len() < MYELON_TYPED_ENVELOPE_HEADER_BYTES {
        return Err(CodecError::decode(format!(
            "typed Myelon envelope too short: {}",
            bytes.len()
        )));
    }
    Ok((bytes[0], &bytes[MYELON_TYPED_ENVELOPE_HEADER_BYTES..]))
}

impl Codec for TypedMyelonRequest {
    type Encoded = Vec<u8>;

    fn encode(&self) -> Result<Self::Encoded, CodecError> {
        let payload = self.0.encode().map_err(CodecError::encode)?;
        Ok(encode_envelope(self.0.kind().as_u8(), &payload))
    }

    fn decode(bytes: &[u8]) -> Result<Self, CodecError> {
        let (tag, payload) = decode_envelope(bytes)?;
        let request = MyelonRequest::decode(tag, payload).map_err(CodecError::decode)?;
        Ok(Self(request))
    }
}

impl Codec for TypedMyelonResponse {
    type Encoded = Vec<u8>;

    fn encode(&self) -> Result<Self::Encoded, CodecError> {
        let payload = self.0.encode().map_err(CodecError::encode)?;
        Ok(encode_envelope(self.0.kind().as_u8(), &payload))
    }

    fn decode(bytes: &[u8]) -> Result<Self, CodecError> {
        let (tag, payload) = decode_envelope(bytes)?;
        let response = MyelonResponse::decode(tag, payload).map_err(CodecError::decode)?;
        Ok(Self(response))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::utils::config::SamplingParams;

    #[test]
    fn typed_request_round_trip_preserves_prefill_payload() {
        let request = TypedMyelonRequest(MyelonRequest::RunPrefill {
            sequences: vec![crate::core::sequence::Sequence::new(
                vec![1, 2, 3, 4],
                16,
                SamplingParams::default(),
                &None,
                0,
            )],
        });

        let bytes = request.encode().unwrap();
        let decoded = TypedMyelonRequest::decode(&bytes).unwrap().into_inner();

        match decoded {
            MyelonRequest::RunPrefill { sequences } => {
                assert_eq!(sequences.len(), 1);
                assert_eq!(sequences[0].token_ids, vec![1, 2, 3, 4]);
            }
            other => panic!("unexpected decoded request: {other:?}"),
        }
    }

    #[test]
    fn typed_response_round_trip_preserves_run_outputs() {
        let response = TypedMyelonResponse(MyelonResponse::RunResponse(vec![7, 8, 9]));

        let bytes = response.encode().unwrap();
        let decoded = TypedMyelonResponse::decode(&bytes).unwrap().into_inner();

        match decoded {
            MyelonResponse::RunResponse(output_ids) => assert_eq!(output_ids, vec![7, 8, 9]),
            other => panic!("unexpected decoded response: {other:?}"),
        }
    }

    #[test]
    fn typed_envelope_rejects_short_payloads() {
        let error = TypedMyelonRequest::decode(&[1, 2, 3])
            .unwrap_err()
            .to_string();
        assert!(error.contains("typed Myelon envelope too short"));
    }
}
