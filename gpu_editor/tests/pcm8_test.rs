use gpu_editor::{Command, Regs};
use wgpu::util::DeviceExt;

#[test]
fn test_rect_command() {
    pollster::block_on(run_rect_test());
}

#[test]
fn test_cppm_read_opcode() {
    pollster::block_on(run_cppm_read_test());
}

async fn run_rect_test() {
    let instance = wgpu::Instance::new(wgpu::InstanceDescriptor::default());
    let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions::default()).await.unwrap();
    let (device, queue) = adapter.request_device(&wgpu::DeviceDescriptor::default(), None).await.unwrap();

    let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("PCM-8 Shader"),
        source: wgpu::ShaderSource::Wgsl(include_str!("../src/pcmd.wgsl").into()),
    });

    const CMDQ_CAPACITY: u32 = 4096;
    let cmdq_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Command Queue Buffer"),
        size: (CMDQ_CAPACITY * std::mem::size_of::<Command>() as u32) as u64,
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    let initial_regs = Regs::new(CMDQ_CAPACITY);
    let regs_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("Registers Buffer"),
        contents: bytemuck::cast_slice(&[initial_regs]),
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
    });

    const TEXTURE_WIDTH: u32 = 1024;
    const TEXTURE_HEIGHT: u32 = 1024;
    let work_texture = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Work Texture"),
        size: wgpu::Extent3d { width: TEXTURE_WIDTH, height: TEXTURE_HEIGHT, depth_or_array_layers: 1 },
        mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rgba8Uint,
        usage: wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    });
    let work_texture_view = work_texture.create_view(&wgpu::TextureViewDescriptor::default());

    // For this test, we don't need the inbox buffer, but the pipeline expects it.
    let inbox_ascii_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Inbox ASCII Buffer"),
        size: 4,
        usage: wgpu::BufferUsages::STORAGE,
        mapped_at_creation: false,
    });

    let (exec_pipeline, exec_bind_group) = create_compute_pipeline(
        &device, &shader, "exec", &regs_buffer, &cmdq_buffer, &inbox_ascii_buffer, Some(&work_texture_view)
    );

    let mut staging_belt = wgpu::util::StagingBelt::new(1024);
    let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor::default());

    let rect_command = Command {
        op_flags: 0x11,
        params1: (32) | (48 << 16),
        params2: (16) | (16 << 16),
        params3: (255) | (0 << 16),
    };
    staging_belt.write_buffer(&mut encoder, &cmdq_buffer, 0,
        wgpu::BufferSize::new(std::mem::size_of::<Command>() as u64).unwrap(), &device)
        .copy_from_slice(bytemuck::bytes_of(&rect_command));
    staging_belt.write_buffer(&mut encoder, &regs_buffer, 0,
        wgpu::BufferSize::new(4).unwrap(), &device)
        .copy_from_slice(&1u32.to_le_bytes());

    let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor::default());
    cpass.set_pipeline(&exec_pipeline);
    cpass.set_bind_group(0, &exec_bind_group, &[]);
    cpass.dispatch_workgroups(1, 1, 1);
    drop(cpass);

    let output_buffer_size = (TEXTURE_WIDTH * TEXTURE_HEIGHT * 4) as u64;
    let output_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Output Buffer"),
        size: output_buffer_size,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    encoder.copy_texture_to_buffer(
        work_texture.as_image_copy(),
        wgpu::ImageCopyBuffer { buffer: &output_buffer, layout: wgpu::ImageDataLayout {
            offset: 0, bytes_per_row: Some(TEXTURE_WIDTH * 4), rows_per_image: Some(TEXTURE_HEIGHT),
        }},
        work_texture.size(),
    );

    staging_belt.finish();
    queue.submit(Some(encoder.finish()));

    let buffer_slice = output_buffer.slice(..);
    let (tx, rx) = std::sync::mpsc::channel();
    buffer_slice.map_async(wgpu::MapMode::Read, move |result| {
        tx.send(result).unwrap();
    });
    device.poll(wgpu::Maintain::Wait);
    rx.recv().unwrap().unwrap();

    let data = buffer_slice.get_mapped_range();

    // --- Verify REGS state ---
    let regs_output_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Regs Output Buffer"),
        size: std::mem::size_of::<Regs>() as u64,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });

    let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor::default());
    encoder.copy_buffer_to_buffer(&regs_buffer, 0, &regs_output_buffer, 0, std::mem::size_of::<Regs>() as u64);
    queue.submit(Some(encoder.finish()));

    let regs_slice = regs_output_buffer.slice(..);
    let (tx_regs, rx_regs) = std::sync::mpsc::channel();
    regs_slice.map_async(wgpu::MapMode::Read, move |result| {
        tx_regs.send(result).unwrap();
    });
    device.poll(wgpu::Maintain::Wait);
    rx_regs.recv().unwrap().unwrap();

    let regs_mapped_range = regs_slice.get_mapped_range();
    let regs_data: &Regs = bytemuck::from_bytes(&regs_mapped_range);
    assert_eq!(regs_data.head, 1, "Head register should be 1");
    assert_eq!(regs_data.tail, 1, "Tail register should be 1");
    assert_eq!(regs_data.err, 0, "Error register should be 0");
    assert_eq!(regs_data.active_pixel_count, 256, "Active pixel count should be 256");
    assert_eq!(regs_data.cppm_accumulator, 256, "CPPM accumulator should be 256");

    let mut success = true;
    for y in 0..TEXTURE_HEIGHT {
        for x in 0..TEXTURE_WIDTH {
            let i = ((y * TEXTURE_WIDTH + x) * 4) as usize;
            if (x >= 32 && x < 48) && (y >= 48 && y < 64) {
                if data[i] != 255 { success = false; break; }
            } else {
                if data[i] != 0 { success = false; break; }
            }
        }
        if !success { break; }
    }
    assert!(success, "Smoke test FAILED!");
}

async fn run_cppm_read_test() {
    let instance = wgpu::Instance::new(wgpu::InstanceDescriptor::default());
    let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions::default()).await.unwrap();
    let (device, queue) = adapter.request_device(&wgpu::DeviceDescriptor::default(), None).await.unwrap();

    let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("PCM-8 Shader"),
        source: wgpu::ShaderSource::Wgsl(include_str!("../src/pcmd.wgsl").into()),
    });

    const CMDQ_CAPACITY: u32 = 4096;
    let cmdq_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Command Queue Buffer"),
        size: (CMDQ_CAPACITY * std::mem::size_of::<Command>() as u32) as u64,
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    let initial_regs = Regs::new(CMDQ_CAPACITY);
    let regs_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("Registers Buffer"),
        contents: bytemuck::cast_slice(&[initial_regs]),
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
    });

    let work_texture = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Work Texture"),
        size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 },
        mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rgba8Uint,
        usage: wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    });
    let work_texture_view = work_texture.create_view(&wgpu::TextureViewDescriptor::default());

    let inbox_ascii_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Inbox ASCII Buffer"), size: 4, usage: wgpu::BufferUsages::STORAGE, mapped_at_creation: false,
    });

    let (exec_pipeline, exec_bind_group) = create_compute_pipeline(
        &device, &shader, "exec", &regs_buffer, &cmdq_buffer, &inbox_ascii_buffer, Some(&work_texture_view)
    );

    let mut staging_belt = wgpu::util::StagingBelt::new(1024);
    let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor::default());

    let commands = [
        Command { op_flags: 0x11, params1: (0)|(0<<16), params2: (16)|(16<<16), params3: (0)|(0<<16) }, // RECT
        Command { op_flags: 0x07, params1: 0, params2: 0, params3: 0 }, // CPPM_READ
    ];
    staging_belt.write_buffer(&mut encoder, &cmdq_buffer, 0,
        wgpu::BufferSize::new(std::mem::size_of::<Command>() as u64 * 2).unwrap(), &device)
        .copy_from_slice(bytemuck::cast_slice(&commands));
    staging_belt.write_buffer(&mut encoder, &regs_buffer, 0,
        wgpu::BufferSize::new(4).unwrap(), &device)
        .copy_from_slice(&2u32.to_le_bytes()); // Set head to 2

    let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor::default());
    cpass.set_pipeline(&exec_pipeline);
    cpass.set_bind_group(0, &exec_bind_group, &[]);
    cpass.dispatch_workgroups(1, 1, 1);
    drop(cpass);

    staging_belt.finish();
    queue.submit(Some(encoder.finish()));

    let regs_output_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Regs Output Buffer"),
        size: std::mem::size_of::<Regs>() as u64,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor::default());
    encoder.copy_buffer_to_buffer(&regs_buffer, 0, &regs_output_buffer, 0, std::mem::size_of::<Regs>() as u64);
    queue.submit(Some(encoder.finish()));

    let regs_slice = regs_output_buffer.slice(..);
    let (tx, rx) = std::sync::mpsc::channel();
    regs_slice.map_async(wgpu::MapMode::Read, move |result| { tx.send(result).unwrap(); });
    device.poll(wgpu::Maintain::Wait);
    rx.recv().unwrap().unwrap();

    let regs_mapped_range = regs_slice.get_mapped_range();
    let regs_data: &Regs = bytemuck::from_bytes(&regs_mapped_range);
    assert_eq!(regs_data.err, 256, "CPPM_READ should write accumulator value (256) to err register");
}

// Duplicating this function for the test. It should be in the library.
fn create_compute_pipeline(
    device: &wgpu::Device, shader: &wgpu::ShaderModule, entry_point: &str,
    regs_buffer: &wgpu::Buffer, cmdq_buffer: &wgpu::Buffer, inbox_buffer: &wgpu::Buffer,
    work_texture_view: Option<&wgpu::TextureView>,
) -> (wgpu::ComputePipeline, wgpu::BindGroup) {
    let mut entries = vec![
        wgpu::BindGroupLayoutEntry {
            binding: 0, visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None },
            count: None,
        },
        wgpu::BindGroupLayoutEntry {
            binding: 1, visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: wgpu::BufferSize::new(std::mem::size_of::<Command>() as _)},
            count: None,
        },
        wgpu::BindGroupLayoutEntry {
            binding: 2, visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None },
            count: None,
        },
    ];
    if work_texture_view.is_some() {
        entries.push(wgpu::BindGroupLayoutEntry {
            binding: 3, visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format: wgpu::TextureFormat::Rgba8Uint, view_dimension: wgpu::TextureViewDimension::D2 },
            count: None,
        });
    }
    let bind_group_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some(&format!("{} Bind Group Layout", entry_point)),
        entries: &entries,
    });
    let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some(&format!("{} Pipeline Layout", entry_point)),
        bind_group_layouts: &[&bind_group_layout],
        push_constant_ranges: &[],
    });
    let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: Some(&format!("{} Pipeline", entry_point)),
        layout: Some(&pipeline_layout),
        module: &shader, entry_point,
    });
    let mut bg_entries = vec![
        wgpu::BindGroupEntry { binding: 0, resource: regs_buffer.as_entire_binding() },
        wgpu::BindGroupEntry { binding: 1, resource: cmdq_buffer.as_entire_binding() },
        wgpu::BindGroupEntry { binding: 2, resource: inbox_buffer.as_entire_binding() },
    ];
    if let Some(view) = work_texture_view {
        bg_entries.push(wgpu::BindGroupEntry {
            binding: 3, resource: wgpu::BindingResource::TextureView(view),
        });
    }
    let bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some(&format!("{} Bind Group", entry_point)),
        layout: &bind_group_layout,
        entries: &bg_entries,
    });
    (pipeline, bind_group)
}