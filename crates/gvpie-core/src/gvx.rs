use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use wgpu::util::DeviceExt;

#[derive(Serialize, Deserialize, Debug)]
pub struct GvxMeta {
    pub version: String,
    pub text_buffer_size: u64,
    pub code_buffer_size: u64,
    pub state_buffer_size: u64,
}

#[derive(Debug)]
pub struct GvxData {
    pub meta: GvxMeta,
    pub text_data: Vec<u8>,
    pub code_data: Vec<u8>,
    pub state_data: Vec<u8>,
}

async fn read_buffer(device: &wgpu::Device, queue: &wgpu::Queue, buffer: &wgpu::Buffer) -> Result<Vec<u8>> {
    let buffer_slice = buffer.slice(..);
    let (tx, rx) = futures_intrusive::channel::shared::oneshot_channel();
    buffer_slice.map_async(wgpu::MapMode::Read, move |result| {
        tx.send(result).unwrap();
    });
    device.poll(wgpu::Maintain::Wait);
    rx.receive().await.unwrap()?;

    let data = buffer_slice.get_mapped_range().to_vec();
    buffer.unmap();
    Ok(data)
}

pub async fn save_gvx(
    path: impl AsRef<Path>,
    device: &wgpu::Device,
    queue: &wgpu::Queue,
    text_buffer: &wgpu::Buffer,
    code_buffer: &wgpu::Buffer,
    state_buffer: &wgpu::Buffer,
) -> Result<()> {
    let path = path.as_ref();
    fs::create_dir_all(path).context("Failed to create GVX directory")?;

    let meta = GvxMeta {
        version: "0.1.0".to_string(),
        text_buffer_size: text_buffer.size(),
        code_buffer_size: code_buffer.size(),
        state_buffer_size: state_buffer.size(),
    };

    let meta_json = serde_json::to_string_pretty(&meta)?;
    fs::write(path.join("meta.json"), meta_json).context("Failed to write meta.json")?;

    let text_data = read_buffer(device, queue, text_buffer).await?;
    fs::write(path.join("text.bin"), text_data).context("Failed to write text.bin")?;

    let code_data = read_buffer(device, queue, code_buffer).await?;
    fs::write(path.join("code.bin"), code_data).context("Failed to write code.bin")?;

    let state_data = read_buffer(device, queue, state_buffer).await?;
    fs::write(path.join("state.bin"), state_data).context("Failed to write state.bin")?;

    Ok(())
}

pub fn load_gvx(path: impl AsRef<Path>) -> Result<GvxData> {
    let path = path.as_ref();

    let meta_json = fs::read_to_string(path.join("meta.json")).context("Failed to read meta.json")?;
    let meta: GvxMeta = serde_json::from_str(&meta_json)?;

    let text_data = fs::read(path.join("text.bin")).context("Failed to read text.bin")?;
    let code_data = fs::read(path.join("code.bin")).context("Failed to read code.bin")?;
    let state_data = fs::read(path.join("state.bin")).context("Failed to read state.bin")?;

    Ok(GvxData {
        meta,
        text_data,
        code_data,
        state_data,
    })
}