use std::{
    fs,
    path::Path,
    time::{Duration, Instant},
};

use anyhow::Context;
use gvpie::{emit_wgsl, parse_program, tokenize};
use half::f16;
use image::{ImageBuffer, Rgba};
use pollster::block_on;

const GVP_PATH: &str = "examples/minimal.gvp";
const OUT_PNG: &str = "out.png";

/// Holds the WGPU state that persists across hot reloads.
struct State {
    device: wgpu::Device,
    queue: wgpu::Queue,
    texture: wgpu::Texture,
    tex_desc: wgpu::TextureDescriptor<'static>,
    bgl: wgpu::BindGroupLayout,
}

fn main() -> anyhow::Result<()> {
    // --- Manual Hot-Reload Test ---
    let mut state = block_on(setup()).context("Failed to set up initial WGPU state")?;
    println!("✅ Initial setup complete.");

    // --- First Run (Original Shader) ---
    println!("Performing initial render...");
    block_on(reload_and_run(&mut state)).context("Initial run failed")?;
    println!("Initial render complete.");

    // --- Modify the file programmatically ---
    println!("\nModifying DSL file to swap color channels...");
    let new_content = r#"
lang 0.1
texture fb: rgba16f @ 512x512;

kernel render each_pixel {
  let r = f32(pixel.x) / 512.0;
  let g = f32(pixel.y) / 512.0;
  // Swapped r and g
  vec4(g, r, 0.0, 1.0)
}

frame { present render; }
"#;
    fs::write(GVP_PATH, new_content).context("Failed to write modified DSL file")?;
    println!("File modified.");

    // --- Second Run (Hot-reloaded Shader) ---
    println!("Performing manual hot-reload run...");
    let start = Instant::now();
    block_on(reload_and_run(&mut state)).context("Hot-reload run failed")?;
    println!("Manual hot-reload finished in {:?}", start.elapsed());

    Ok(())
}


/// Sets up the persistent WGPU resources that don't change during hot-reloading.
async fn setup() -> anyhow::Result<State> {
    let instance = wgpu::Instance::default();
    let adapter = instance
        .request_adapter(&wgpu::RequestAdapterOptions::default())
        .await
        .context("Failed to find a suitable GPU adapter")?;
    let (device, queue) = adapter
        .request_device(&wgpu::DeviceDescriptor::default(), None)
        .await?;

    // We get dimensions from the initial file parse.
    // In a real app, this might be a fixed size or configured elsewhere.
    let src = fs::read_to_string(GVP_PATH)?;
    let prog = parse_program(tokenize(&src));
    let (width, height) = (prog.texture.width, prog.texture.height);

    let tex_desc = wgpu::TextureDescriptor {
        label: Some("output_texture"),
        size: wgpu::Extent3d { width, height, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rgba16Float,
        usage: wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    };
    let texture = device.create_texture(&tex_desc);

    let bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("bind_group_layout"),
        entries: &[wgpu::BindGroupLayoutEntry {
            binding: 0,
            visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::StorageTexture {
                access: wgpu::StorageTextureAccess::WriteOnly,
                format: wgpu::TextureFormat::Rgba16Float,
                view_dimension: wgpu::TextureViewDimension::D2,
            },
            count: None,
        }],
    });

    Ok(State { device, queue, texture, tex_desc, bgl })
}

/// This function is called on startup and every time the DSL file changes.
/// It recreates only the necessary parts of the pipeline.
async fn reload_and_run(state: &mut State) -> anyhow::Result<()> {
    // 1. Re-compile the DSL to WGSL
    let src = fs::read_to_string(GVP_PATH).context("Failed to read GVP source file")?;
    let prog = parse_program(tokenize(&src));
    let wgsl = emit_wgsl(&prog);

    // Optional: Validate with Naga. This adds latency but is great for debugging.
    #[cfg(feature = "validate")]
    if let Err(e) = naga::front::wgsl::parse_str(&wgsl) {
        return Err(anyhow::anyhow!("Naga validation failed: {e}"));
    }

    // 2. Re-create the shader and pipeline (the "volatile" state)
    let shader = state.device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("dsl_shader"),
        source: wgpu::ShaderSource::Wgsl(wgsl.into()),
    });
    let pipeline_layout = state.device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("pipeline_layout"),
        bind_group_layouts: &[&state.bgl],
        ..Default::default()
    });
    let pipeline = state.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: Some("compute_pipeline"),
        layout: Some(&pipeline_layout),
        module: &shader,
        entry_point: &prog.kernel.name,
        compilation_options: Default::default(),
    });

    // 3. Re-create the bind group (since the texture view is re-created implicitly)
    let tex_view = state.texture.create_view(&wgpu::TextureViewDescriptor::default());
    let bind_group = state.device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("bind_group"),
        layout: &state.bgl,
        entries: &[wgpu::BindGroupEntry {
            binding: 0,
            resource: wgpu::BindingResource::TextureView(&tex_view),
        }],
    });

    // 4. Dispatch the shader
    let mut encoder = state.device.create_command_encoder(&wgpu::CommandEncoderDescriptor::default());
    {
        let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor::default());
        cpass.set_pipeline(&pipeline);
        cpass.set_bind_group(0, &bind_group, &[]);
        let (wgx, wgy) = ((state.tex_desc.size.width + 7) / 8, (state.tex_desc.size.height + 7) / 8);
        cpass.dispatch_workgroups(wgx, wgy, 1);
    }

    // 5. Copy the result to a staging buffer and save to PNG
    save_png(state, encoder)?;

    println!("✅ Wrote gradient to {}", OUT_PNG);
    Ok(())
}

fn align_to_256(n: u32) -> u32 {
    const A: u32 = wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
    (n + A - 1) & !(A - 1)
}

fn save_png(state: &State, mut encoder: wgpu::CommandEncoder) -> anyhow::Result<()> {
    let (width, height) = (state.tex_desc.size.width, state.tex_desc.size.height);
    let bytes_per_pixel = 8;
    let unpadded_bpr = width * bytes_per_pixel;
    let padded_bpr = align_to_256(unpadded_bpr);
    let output_size = padded_bpr as u64 * height as u64;

    let staging_buffer = state.device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("staging_buffer"),
        size: output_size,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });

    encoder.copy_texture_to_buffer(
        state.texture.as_image_copy(),
        wgpu::ImageCopyBuffer {
            buffer: &staging_buffer,
            layout: wgpu::ImageDataLayout {
                offset: 0,
                bytes_per_row: Some(padded_bpr),
                rows_per_image: Some(height),
            },
        },
        state.tex_desc.size,
    );

    state.queue.submit(Some(encoder.finish()));
    state.device.poll(wgpu::Maintain::Wait);

    let slice = staging_buffer.slice(..);
    slice.map_async(wgpu::MapMode::Read, |_| {});
    state.device.poll(wgpu::Maintain::Wait);
    let data = slice.get_mapped_range();

    let mut img: ImageBuffer<Rgba<u8>, Vec<u8>> = ImageBuffer::new(width, height);
    for y in 0..height {
        let row_start = (y * padded_bpr) as usize;
        let row_end = row_start + unpadded_bpr as usize;
        let row_data = &data[row_start..row_end];

        for (x, pixel) in img.pixels_mut().skip((y * width) as usize).take(width as usize).enumerate() {
            let offset = x * bytes_per_pixel as usize;
            let r_half = f16::from_le_bytes([row_data[offset], row_data[offset + 1]]);
            let g_half = f16::from_le_bytes([row_data[offset + 2], row_data[offset + 3]]);
            let b_half = f16::from_le_bytes([row_data[offset + 4], row_data[offset + 5]]);
            let a_half = f16::from_le_bytes([row_data[offset + 6], row_data[offset + 7]]);

            let to_u8 = |v: f32| (v.clamp(0.0, 1.0) * 255.0 + 0.5) as u8;
            *pixel = Rgba([to_u8(r_half.to_f32()), to_u8(g_half.to_f32()), to_u8(b_half.to_f32()), to_u8(a_half.to_f32())]);
        }
    }
    drop(data);
    staging_buffer.unmap();

    img.save(Path::new(OUT_PNG))?;
    Ok(())
}