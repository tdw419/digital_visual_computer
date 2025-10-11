use anyhow::Result;
use bytemuck::{Pod, Zeroable};
use gvpie_core::gvx;
use gvpie_gpu::{load_exec_ops_shader, load_parse_text_to_ops_shader};
use winit::{
    event::{ElementState, Event, KeyEvent, WindowEvent},
    event_loop::{ControlFlow, EventLoop},
    keyboard::{Key, ModifiersState},
    window::{Window, WindowBuilder},
};
use wgpu::util::DeviceExt;

struct State<'a> {
    surface: wgpu::Surface<'a>,
    device: wgpu::Device,
    queue: wgpu::Queue,
    config: wgpu::SurfaceConfiguration,
    size: winit::dpi::PhysicalSize<u32>,
    window: &'a Window,

    // GVPIE Resources
    text_buffer: wgpu::Buffer,
    code_buffer: wgpu::Buffer,
    state_buffer: wgpu::Buffer,
    frame_texture: wgpu::Texture,

    // Pipelines
    parser_pipeline: wgpu::ComputePipeline,
    executor_pipeline: wgpu::ComputePipeline,
    render_pipeline: wgpu::RenderPipeline,

    // Bind Groups
    parser_bind_group: wgpu::BindGroup,
    executor_bind_group: wgpu::BindGroup,
    render_bind_group: wgpu::BindGroup,

    // Host-side state
    text: Vec<u32>,
    modifiers: winit::keyboard::ModifiersState,
}

impl<'a> State<'a> {
    async fn new(window: &'a Window) -> Self {
        let size = window.inner_size();

        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
            backends: wgpu::Backends::all(),
            ..Default::default()
        });

        let surface = instance.create_surface(window).unwrap();

        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::default(),
                compatible_surface: Some(&surface),
                force_fallback_adapter: false,
            })
            .await
            .unwrap();

        let (device, queue) = adapter
            .request_device(
                &wgpu::DeviceDescriptor {
                    required_features: wgpu::Features::empty(),
                    required_limits: wgpu::Limits::default(),
                    label: None,
                },
                None,
            )
            .await
            .unwrap();

        let surface_caps = surface.get_capabilities(&adapter);
        let surface_format = surface_caps
            .formats
            .iter()
            .copied()
            .find(|f| f.is_srgb())
            .unwrap_or(surface_caps.formats[0]);
        let config = wgpu::SurfaceConfiguration {
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            format: surface_format,
            width: size.width,
            height: size.height,
            present_mode: surface_caps.present_modes[0],
            alpha_mode: surface_caps.alpha_modes[0],
            view_formats: vec![],
            desired_maximum_frame_latency: 2,
        };
        surface.configure(&device, &config);

        // --- GVPIE Resources ---
        let (text_buffer, code_buffer, state_buffer, text) =
            if let Ok(gvx_data) = gvx::load_gvx("program.gvx") {
                log::info!("Loaded program from program.gvx");
                let text_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("Text Buffer"),
                    contents: &gvx_data.text_data,
                    usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
                });
                let code_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("Code Buffer"),
                    contents: &gvx_data.code_data,
                    usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
                });
                let state_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("State Buffer"),
                    contents: &gvx_data.state_data,
                    usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
                });
                let text: Vec<u32> = bytemuck::cast_slice(&gvx_data.text_data).to_vec();
                (text_buffer, code_buffer, state_buffer, text)
            } else {
                log::info!("No program.gvx found, starting new program.");
                // Initial state: IP=0, op_count=0, cursor_x=0, cursor_y=0, reserved, text_len=0
                let initial_state_data = [0u32, 0, 0, 0, 0, 0];
                let state_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("State Buffer"),
                    contents: bytemuck::cast_slice(&initial_state_data),
                    usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
                });

                let code_buffer = device.create_buffer(&wgpu::BufferDescriptor {
                    label: Some("Code Buffer"),
                    size: 1024 * 4, // 1024 instructions
                    usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
                    mapped_at_creation: false,
                });

                let text_buffer = device.create_buffer(&wgpu::BufferDescriptor {
                    label: Some("Text Buffer"),
                    size: 1024 * 4, // 1024 chars
                    usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC,
                    mapped_at_creation: false,
                });
                (text_buffer, code_buffer, state_buffer, Vec::new())
            };


        let frame_texture = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("Frame Texture"),
            size: wgpu::Extent3d {
                width: size.width,
                height: size.height,
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::Rgba8Unorm,
            usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::STORAGE_BINDING,
            view_formats: &[],
        });
        let frame_texture_view = frame_texture.create_view(&wgpu::TextureViewDescriptor::default());

        // --- Parser Pipeline ---
        let parser_shader = load_parse_text_to_ops_shader(&device);
        let parser_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                entries: &[
                    // TEXT
                    wgpu::BindGroupLayoutEntry {
                        binding: 0,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: true },
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                    // CODE
                    wgpu::BindGroupLayoutEntry {
                        binding: 1,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: false },
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                    // STATE
                    wgpu::BindGroupLayoutEntry {
                        binding: 2,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: false },
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                ],
                label: Some("Parser Bind Group Layout"),
            });

        let parser_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            layout: &parser_bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: text_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: code_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: state_buffer.as_entire_binding(),
                },
            ],
            label: Some("Parser Bind Group"),
        });

        let parser_pipeline_layout =
            device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("Parser Pipeline Layout"),
                bind_group_layouts: &[&parser_bind_group_layout],
                push_constant_ranges: &[],
            });

        let parser_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("Parser Pipeline"),
            layout: Some(&parser_pipeline_layout),
            module: &parser_shader,
            entry_point: "parse_text_to_ops",
        });

        // --- Executor Pipeline ---
        let exec_shader = load_exec_ops_shader(&device);
        let executor_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                entries: &[
                    wgpu::BindGroupLayoutEntry {
                        binding: 0,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: false },
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                    wgpu::BindGroupLayoutEntry {
                        binding: 1,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: false },
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                    wgpu::BindGroupLayoutEntry {
                        binding: 2,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::StorageTexture {
                            access: wgpu::StorageTextureAccess::WriteOnly,
                            format: wgpu::TextureFormat::Rgba8Unorm,
                            view_dimension: wgpu::TextureViewDimension::D2,
                        },
                        count: None,
                    },
                ],
                label: Some("Executor Bind Group Layout"),
            });

        let executor_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            layout: &executor_bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: code_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: state_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: wgpu::BindingResource::TextureView(&frame_texture_view),
                },
            ],
            label: Some("Executor Bind Group"),
        });

        let executor_pipeline_layout =
            device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("Executor Pipeline Layout"),
                bind_group_layouts: &[&executor_bind_group_layout],
                push_constant_ranges: &[],
            });

        let executor_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("Executor Pipeline"),
            layout: Some(&executor_pipeline_layout),
            module: &exec_shader,
            entry_point: "exec_ops",
        });

        // --- Render Pipeline ---
        let render_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Render Shader"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shader.wgsl").into()),
        });

        let render_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                entries: &[wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Texture {
                        multisampled: false,
                        view_dimension: wgpu::TextureViewDimension::D2,
                        sample_type: wgpu::TextureSampleType::Float { filterable: true },
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering),
                    count: None,
                }],
                label: Some("Render Bind Group Layout"),
            });

        let sampler = device.create_sampler(&wgpu::SamplerDescriptor::default());
        let render_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            layout: &render_bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: wgpu::BindingResource::TextureView(&frame_texture_view),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: wgpu::BindingResource::Sampler(&sampler),
                },
            ],
            label: Some("Render Bind Group"),
        });

        let render_pipeline_layout =
            device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("Render Pipeline Layout"),
                bind_group_layouts: &[&render_bind_group_layout],
                push_constant_ranges: &[],
            });

        let render_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("Render Pipeline"),
            layout: Some(&render_pipeline_layout),
            vertex: wgpu::VertexState {
                module: &render_shader,
                entry_point: "vs_main",
                buffers: &[],
            },
            fragment: Some(wgpu::FragmentState {
                module: &render_shader,
                entry_point: "fs_main",
                targets: &[Some(wgpu::ColorTargetState {
                    format: config.format,
                    blend: Some(wgpu::BlendState::REPLACE),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
        });

        Self {
            window,
            surface,
            device,
            queue,
            config,
            size,
            text_buffer,
            code_buffer,
            state_buffer,
            frame_texture,
            parser_pipeline,
            executor_pipeline,
            render_pipeline,
            parser_bind_group,
            executor_bind_group,
            render_bind_group,
            text,
            modifiers: ModifiersState::empty(),
        }
    }

    pub fn window(&self) -> &'a Window {
        &self.window
    }

    fn resize(&mut self, new_size: winit::dpi::PhysicalSize<u32>) {
        if new_size.width > 0 && new_size.height > 0 {
            self.size = new_size;
            self.config.width = new_size.width;
            self.config.height = new_size.height;
            self.surface.configure(&self.device, &self.config);
        }
    }

    fn input(&mut self, event: &WindowEvent) -> bool {
        match event {
            WindowEvent::ModifiersChanged(new_modifiers) => {
                self.modifiers = new_modifiers.state();
                false
            }
            WindowEvent::KeyboardInput {
                event:
                    KeyEvent {
                        state: ElementState::Pressed,
                        physical_key: _,
                        logical_key,
                        ..
                    },
                ..
            } => {
                if self.modifiers.control_key() {
                     if let Key::Character(s) = logical_key.as_ref() {
                        if s == "s" {
                            log::info!("Saving program state...");
                            pollster::block_on(gvx::save_gvx(
                                "program.gvx",
                                &self.device,
                                &self.queue,
                                &self.text_buffer,
                                &self.code_buffer,
                                &self.state_buffer,
                            )).expect("Failed to save GVX bundle");
                            log::info!("Program state saved to program.gvx");
                            return true;
                        }
                    }
                }

                let char_code = match logical_key.as_ref() {
                    Key::Character("x") => 'X' as u32,
                    Key::Character("0") => '0' as u32,
                    Key::Character("1") => '1' as u32,
                    Key::Character("2") => '2' as u32,
                    Key::Character("3") => '3' as u32,
                    Key::Character("4") => '4' as u32,
                    Key::Character("5") => '5' as u32,
                    Key::Character("6") => '6' as u32,
                    Key::Character("7") => '7' as u32,
                    Key::Character("8") => '8' as u32,
                    Key::Character("9") => '9' as u32,
                    _ => return false,
                };
                self.text.push(char_code);
                true
            }
            _ => false,
        }
    }

    fn update(&mut self) {
        // Reset op_count and ip
        self.queue.write_buffer(&self.state_buffer, 0, bytemuck::cast_slice(&[0u32, 0]));
        // Write text to buffer
        self.queue.write_buffer(&self.text_buffer, 0, bytemuck::cast_slice(&self.text));
        // Write text_len
        self.queue.write_buffer(&self.state_buffer, 20, bytemuck::cast_slice(&[self.text.len() as u32]));
    }

    fn render(&mut self) -> Result<(), wgpu::SurfaceError> {
        let output = self.surface.get_current_texture()?;
        let view = output
            .texture
            .create_view(&wgpu::TextureViewDescriptor::default());
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("Render Encoder"),
            });

        // Parser Pass
        {
            let mut compute_pass =
                encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("Parser Pass"), timestamp_writes: None });
            compute_pass.set_pipeline(&self.parser_pipeline);
            compute_pass.set_bind_group(0, &self.parser_bind_group, &[]);
            let workgroup_count = (self.text.len() as u32 + 63) / 64;
            compute_pass.dispatch_workgroups(workgroup_count, 1, 1);
        }

        // Executor Pass
        {
            let mut compute_pass =
                encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("Executor Pass"), timestamp_writes: None });
            compute_pass.set_pipeline(&self.executor_pipeline);
            compute_pass.set_bind_group(0, &self.executor_bind_group, &[]);
            compute_pass.dispatch_workgroups(1, 1, 1);
        }

        // Render Pass
        {
            let mut render_pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("Render Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color {
                            r: 0.1,
                            g: 0.2,
                            b: 0.3,
                            a: 1.0,
                        }),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });

            render_pass.set_pipeline(&self.render_pipeline);
            render_pass.set_bind_group(0, &self.render_bind_group, &[]);
            render_pass.draw(0..3, 0..1);
        }

        self.queue.submit(std::iter::once(encoder.finish()));
        output.present();

        Ok(())
    }
}

fn main() -> Result<()> {
    env_logger::init();
    let event_loop = EventLoop::new().unwrap();
    let window = WindowBuilder::new().build(&event_loop).unwrap();
    let mut state = pollster::block_on(State::new(&window));

    event_loop.run(move |event, elwt| {
        match event {
            Event::WindowEvent {
                ref event,
                window_id,
            } if window_id == state.window().id() => {
                if !state.input(event) {
                    match event {
                        WindowEvent::CloseRequested => elwt.exit(),
                        WindowEvent::Resized(physical_size) => {
                            state.resize(*physical_size);
                        }
                        _ => {}
                    }
                }
            }
            Event::AboutToWait => {
                state.window.request_redraw();
            }
            Event::WindowEvent {
                event: WindowEvent::RedrawRequested,
                ..
            } => {
                state.update();
                match state.render() {
                    Ok(_) => {}
                    Err(wgpu::SurfaceError::Lost) => state.resize(state.size),
                    Err(wgpu::SurfaceError::OutOfMemory) => elwt.exit(),
                    Err(e) => eprintln!("{:?}", e),
                }
            }
            _ => {}
        }
    }).unwrap();

    Ok(())
}