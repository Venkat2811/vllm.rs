#[cfg(feature = "myelon-flatbuf")]
#[allow(unused_imports, clippy::all, dead_code)]
mod myelon_ipc_generated;

#[cfg(feature = "myelon-flatbuf")]
pub use myelon_ipc_generated::myelon::ipc::*;
