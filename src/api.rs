use crate::core::engine::{LLMEngine, StreamItem, GLOBAL_RT};
use crate::core::GenerationOutput;
use crate::server::{build_messages_and_images, run_server, ChatMessage};
use crate::tools::Tool;
use crate::utils::chat_template::Message;
use crate::utils::config::{EngineConfig, SamplingParams};
use crate::utils::get_dtype;
use candle_core::{DType, Result};
use parking_lot::RwLock;
use std::str::FromStr;
use std::sync::Arc;
use tokio::sync::mpsc;

#[derive(Clone, Debug)]
pub enum ModelRepo {
    /// (model_id, filename) -- when filename is None, treat as safetensor model id.
    /// When filename is Some, treat as GGUF model id + GGUF filename.
    ModelID((&'static str, Option<&'static str>)),
    /// Safetensor local path.
    ModelPath(&'static str),
    /// GGUF file(s). Only the first file is used today.
    ModelFile(Vec<&'static str>),
}

#[derive(Clone, Debug)]
pub struct EngineBuilder {
    repo: ModelRepo,
    isq: Option<String>,
    dtype: Option<DType>,
    flash_attn: Option<bool>,
    fp8_kvcache: Option<bool>,
    mamba_fraction: Option<f32>,
    prefix_cache: Option<bool>,
    prefix_cache_max_tokens: Option<usize>,
    pd_server_prefix_cache_ratio: Option<f32>,
    pd_client_prefix_cache_ratio: Option<f32>,
    yarn_scaling_factor: Option<f64>,
    num_shards: Option<usize>,
    device_ids: Option<Vec<usize>>,
    force_runner: Option<bool>,
    myelon_ipc: Option<bool>,
    myelon_rpc_depth: Option<usize>,
    myelon_response_depth: Option<usize>,
    myelon_busy_spin: Option<bool>,
}

impl EngineBuilder {
    pub fn new(repo: ModelRepo) -> Self {
        Self {
            repo,
            isq: None,
            dtype: None,
            flash_attn: None,
            fp8_kvcache: None,
            mamba_fraction: None,
            prefix_cache: None,
            prefix_cache_max_tokens: None,
            pd_server_prefix_cache_ratio: None,
            pd_client_prefix_cache_ratio: None,
            yarn_scaling_factor: None,
            num_shards: None,
            device_ids: None,
            force_runner: None,
            myelon_ipc: None,
            myelon_rpc_depth: None,
            myelon_response_depth: None,
            myelon_busy_spin: None,
        }
    }

    pub fn with_isq(mut self, isq: impl Into<String>) -> Self {
        self.isq = Some(isq.into());
        self
    }

    pub fn with_dtype(mut self, dtype: DType) -> Self {
        self.dtype = Some(dtype);
        self
    }

    pub fn without_flash_attn(mut self) -> Self {
        self.flash_attn = Some(false);
        self
    }

    pub fn with_fp8_kvcache(mut self) -> Self {
        self.fp8_kvcache = Some(true);
        self
    }

    pub fn with_mamba_fraction(mut self, ratio: f32) -> Self {
        self.mamba_fraction = Some(ratio);
        self
    }

    pub fn with_prefix_cache(mut self, enabled: bool) -> Self {
        self.prefix_cache = Some(enabled);
        self
    }

    pub fn with_prefix_cache_max_tokens(mut self, max_tokens: usize) -> Self {
        self.prefix_cache_max_tokens = Some(max_tokens);
        self
    }

    pub fn with_pd_server_prefix_cache_ratio(mut self, ratio: f32) -> Self {
        self.pd_server_prefix_cache_ratio = Some(ratio);
        self
    }

    pub fn with_pd_client_prefix_cache_ratio(mut self, ratio: f32) -> Self {
        self.pd_client_prefix_cache_ratio = Some(ratio);
        self
    }

    pub fn with_num_shards(mut self, num_shards: usize) -> Self {
        self.num_shards = Some(num_shards);
        self
    }

    pub fn with_device_ids(mut self, device_ids: Vec<usize>) -> Self {
        self.device_ids = Some(device_ids);
        self
    }

    pub fn with_yarn_scaling_factor(mut self, factor: f64) -> Self {
        self.yarn_scaling_factor = Some(factor);
        self
    }

    pub fn with_multirank(mut self, device_ids: &str) -> Result<Self> {
        self.device_ids = Some(parse_device_ids(device_ids)?);
        Ok(self)
    }

    pub fn with_force_runner(mut self, enabled: bool) -> Self {
        self.force_runner = Some(enabled);
        self
    }

    pub fn with_myelon_ipc(mut self, enabled: bool) -> Self {
        self.myelon_ipc = Some(enabled);
        self
    }

    pub fn with_myelon_rpc_depth(mut self, depth: usize) -> Self {
        self.myelon_rpc_depth = Some(depth);
        self
    }

    pub fn with_myelon_response_depth(mut self, depth: usize) -> Self {
        self.myelon_response_depth = Some(depth);
        self
    }

    pub fn with_myelon_busy_spin(mut self, enabled: bool) -> Self {
        self.myelon_busy_spin = Some(enabled);
        self
    }

    fn resolve_repo(&self) -> (Option<String>, Option<String>, Option<String>) {
        match self.repo.clone() {
            ModelRepo::ModelID((model_id, filename)) => (
                Some(model_id.to_owned()),
                None,
                filename.map(|f| f.to_owned()),
            ),
            ModelRepo::ModelPath(path) => (None, Some(path.to_owned()), None),
            ModelRepo::ModelFile(files) => {
                if files.len() > 1 {
                    crate::log_warn!("Multiple GGUF files provided, using the first one.");
                }
                let weight_file = files.into_iter().next().map(|f| f.to_owned());
                (None, None, weight_file)
            }
        }
    }

    fn build_engine_config(&self) -> EngineConfig {
        let (model_id, weight_path, weight_file) = self.resolve_repo();
        let force_runner = self.force_runner.unwrap_or(false) || self.myelon_ipc.unwrap_or(false);
        EngineConfig::new(
            model_id,
            weight_path,
            weight_file,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            self.isq.clone(),
            self.num_shards,
            self.device_ids.clone(),
            Some(force_runner),
            self.myelon_ipc,
            self.myelon_rpc_depth,
            self.myelon_response_depth,
            self.myelon_busy_spin,
            None,
            None,
            self.prefix_cache,
            self.prefix_cache_max_tokens,
            self.fp8_kvcache,
            None,
            None,
            None,
            self.mamba_fraction,
            None,
            None,
            None,
            None,
            None,
            self.pd_server_prefix_cache_ratio,
            self.pd_client_prefix_cache_ratio,
            self.yarn_scaling_factor,
        )
    }

    pub fn build(self) -> Result<Engine> {
        let econfig = self.build_engine_config();
        let dtype = self.dtype.clone().map(dtype_to_str);
        let dtype = get_dtype(dtype);

        let engine = LLMEngine::new(&econfig, dtype)?;
        Ok(Engine { engine, econfig })
    }
}

pub struct Engine {
    engine: Arc<RwLock<LLMEngine>>,
    econfig: EngineConfig,
}

impl Engine {
    pub fn shutdown(&mut self) -> Result<()> {
        let mut engine = self.engine.write();
        engine.shutdown()
    }

    pub fn start_server(&mut self, port: usize, with_ui_server: bool) -> Result<()> {
        let result = GLOBAL_RT.block_on(async {
            run_server(
                self.engine.clone(),
                self.econfig.clone(),
                port,
                with_ui_server,
            )
            .await
        });
        self.shutdown()?;
        result
    }

    pub fn generate(
        &mut self,
        params: SamplingParams,
        messages: Vec<ChatMessage>,
        tools: Vec<Tool>,
    ) -> Result<GenerationOutput> {
        let img_cfg = { self.engine.read().img_cfg.clone() };
        let (messages, image_data) = build_messages_and_images(&messages, img_cfg.as_ref())?;
        self.generate_messages(params, messages, image_data, tools)
    }

    pub fn generate_messages(
        &mut self,
        params: SamplingParams,
        messages: Vec<Message>,
        images: Option<crate::utils::image::ImageData>,
        tools: Vec<Tool>,
    ) -> Result<GenerationOutput> {
        let (receivers, tokenizer) = {
            let mut engine = self.engine.write();
            (
                engine.generate_sync(&vec![params], &vec![messages], images, &tools, &None)?,
                Arc::new(engine.tokenizer.clone()),
            )
        };

        let results = GLOBAL_RT.block_on(async {
            LLMEngine::collect_sync_results(receivers, tokenizer, None).await
        })?;

        // Extract GenerationOutput
        for result in results {
            return Ok(result);
        }

        candle_core::bail!("No generation output returned")
    }

    pub fn generate_stream(
        &mut self,
        params: SamplingParams,
        messages: Vec<ChatMessage>,
        tools: Vec<Tool>,
    ) -> Result<EngineStream> {
        let img_cfg = { self.engine.read().img_cfg.clone() };
        let (messages, image_data) = build_messages_and_images(&messages, img_cfg.as_ref())?;

        let (seq_id, prompt_length, _prefilled_reasoning_end, stream) = {
            let mut engine = self.engine.write();
            engine.generate_stream(&params, &messages, image_data, &tools, &None)?
        };

        Ok(EngineStream {
            engine: self.engine.clone(),
            rx: stream,
            finished: false,
            seq_id,
            prompt_length,
            cancelled: false,
        })
    }

    pub fn get_num_cached_tokens(&self) -> usize {
        let engine = self.engine.read();
        engine.get_num_cached_tokens()
    }

    pub fn get_available_kv_tokens(&self) -> usize {
        let engine = self.engine.read();
        engine.get_available_kv_tokens()
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        if let Err(error) = self.shutdown() {
            crate::log_warn!("engine shutdown during drop failed: {:?}", error);
        }
    }
}

pub struct EngineStream {
    engine: Arc<RwLock<LLMEngine>>,
    rx: mpsc::Receiver<StreamItem>,
    finished: bool,
    pub seq_id: usize,
    pub prompt_length: usize,
    cancelled: bool,
}

impl EngineStream {
    pub fn cancel(&mut self) {
        self.cancelled = true;
        let mut engine_guard = self.engine.write();
        engine_guard.cancel(self.seq_id);
    }

    pub async fn recv(&mut self) -> Option<StreamItem> {
        if self.finished {
            return None;
        }
        let item = self.rx.recv().await;
        if matches!(item, Some(StreamItem::Done(_) | StreamItem::Error(_))) {
            self.finished = true;
        }
        item
    }

    pub fn recv_blocking(&mut self) -> Option<StreamItem> {
        if self.finished {
            return None;
        }
        let item = GLOBAL_RT.block_on(self.rx.recv());
        if matches!(item, Some(StreamItem::Done(_) | StreamItem::Error(_))) {
            self.finished = true;
        }
        item
    }

    pub fn is_finished(&self) -> bool {
        self.finished
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancelled
    }
}

fn parse_device_ids(device_ids: &str) -> Result<Vec<usize>> {
    let mut parsed = Vec::new();
    for raw in device_ids.split(',') {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            candle_core::bail!("Invalid device id list '{device_ids}': empty entry");
        }
        let value = usize::from_str(trimmed)
            .map_err(|e| candle_core::Error::msg(format!("Invalid device id '{raw}': {e}")))?;
        parsed.push(value);
    }
    Ok(parsed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builder_enables_force_runner_when_myelon_ipc_is_set() {
        let builder = EngineBuilder::new(ModelRepo::ModelPath("/tmp/model"))
            .with_force_runner(false)
            .with_myelon_ipc(true);

        let econfig = builder.build_engine_config();
        assert_eq!(econfig.myelon_ipc, Some(true));
        assert_eq!(econfig.force_runner, Some(true));
    }

    #[test]
    fn builder_preserves_explicit_runner_mode_without_myelon() {
        let builder = EngineBuilder::new(ModelRepo::ModelPath("/tmp/model"))
            .with_force_runner(true)
            .with_myelon_ipc(false);

        let econfig = builder.build_engine_config();
        assert_eq!(econfig.myelon_ipc, Some(false));
        assert_eq!(econfig.force_runner, Some(true));
    }

    #[test]
    fn builder_parses_multirank_device_ids() {
        let builder = EngineBuilder::new(ModelRepo::ModelPath("/tmp/model"))
            .with_num_shards(2)
            .with_multirank("0,1")
            .unwrap();

        let econfig = builder.build_engine_config();
        assert_eq!(econfig.num_shards, Some(2));
        assert_eq!(econfig.device_ids, Some(vec![0, 1]));
    }

    #[test]
    fn parse_device_ids_rejects_empty_entries() {
        let error = parse_device_ids("0,,1").unwrap_err().to_string();
        assert!(error.contains("empty entry"));
    }
}

fn dtype_to_str(dtype: DType) -> String {
    match dtype {
        DType::F16 => "f16".to_string(),
        DType::BF16 => "bf16".to_string(),
        DType::F32 => "f32".to_string(),
        _ => "bf16".to_string(),
    }
}
