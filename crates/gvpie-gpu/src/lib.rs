use wgpu::ShaderModule;

pub fn load_exec_ops_shader(device: &wgpu::Device) -> ShaderModule {
    let shader_source = include_str!("shaders/exec_ops.wgsl");
    device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("Exec Ops Shader"),
        source: wgpu::ShaderSource::Wgsl(shader_source.into()),
    })
}

pub fn load_parse_text_to_ops_shader(device: &wgpu::Device) -> ShaderModule {
    let shader_source = include_str!("shaders/parse_text_to_ops.wgsl");
    device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("Parse Text to Ops Shader"),
        source: wgpu::ShaderSource::Wgsl(shader_source.into()),
    })
}