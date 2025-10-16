use wgpu::util::DeviceExt;

#[repr(C, align(16))]
#[derive(Debug, Copy, Clone, bytemuck::Pod, bytemuck::Zeroable)]
pub struct Regs {
    pub head: u32,
    pub tail: u32,
    pub cap_pow2: u32,
    pub err: u32,
    pub cppm_accumulator: u32,
    pub active_pixel_count: u32,
    pub cppm_budget: u32,
    _padding1: u32,
}

impl Regs {
    pub fn new(cap_pow2: u32) -> Self {
        Self {
            head: 0,
            tail: 0,
            cap_pow2,
            err: 0,
            cppm_accumulator: 0,
            active_pixel_count: 0,
            cppm_budget: 0,
            _padding1: 0,
        }
    }
}

#[repr(C, align(16))]
#[derive(Debug, Copy, Clone, bytemuck::Pod, bytemuck::Zeroable)]
pub struct Command {
    pub op_flags: u32,
    pub params1: u32, // a: u16, b: u16
    pub params2: u32, // c: u16, d: u16
    pub params3: u32, // v0: u16, v1: u16
}

pub struct Pcm8 {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub shader: wgpu::ShaderModule,
    pub regs_buffer: wgpu::Buffer,
    pub cmdq_buffer: wgpu::Buffer,
    pub inbox_ascii_buffer: wgpu::Buffer,
    pub work_texture: wgpu::Texture,
    pub work_texture_view: wgpu::TextureView,
}

impl Pcm8 {
    pub async fn new() -> Self {
        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor::default());
        let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions::default()).await.unwrap();
        let (device, queue) = adapter.request_device(&wgpu::DeviceDescriptor::default(), None).await.unwrap();

        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("PCM-8 Shader"),
            source: wgpu::ShaderSource::Wgsl(include_str!("pcmd.wgsl").into()),
        });

        const CMDQ_CAPACITY: u32 = 4096;
        let inbox_ascii_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Inbox ASCII Buffer"),
            size: 4096 * 4,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
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
            size: wgpu::Extent3d { width: 1024, height: 1024, depth_or_array_layers: 1 },
            mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::Rgba8Uint,
            usage: wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        let work_texture_view = work_texture.create_view(&wgpu::TextureViewDescriptor::default());

        Self {
            device,
            queue,
            shader,
            regs_buffer,
            cmdq_buffer,
            inbox_ascii_buffer,
            work_texture,
            work_texture_view,
        }
    }
}

// The main run function is now just for demonstration purposes.
// The primary verification is done via integration tests.
pub async fn run() {
    println!("GPU Editor running. Primary verification is in integration tests.");
    let _pcm8 = Pcm8::new().await;
    println!("PCM-8 resources initialized.");
}