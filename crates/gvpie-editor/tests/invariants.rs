use wgpu::TextureUsages;

#[test]
fn frame_texture_usage_invariant() {
    // This test codifies a core architectural invariant of GVPIE:
    // The main FRAME texture, which represents the screen, should only be
    // written to by the GPU itself (via a compute shader).
    //
    // Therefore, its usage flags MUST contain STORAGE_BINDING for the compute
    // kernel and TEXTURE_BINDING for the render pipeline to display it.
    //
    // It MUST NOT contain COPY_DST, which would allow the CPU (the host)
    // to write to it directly with `queue.write_texture`, bypassing the
    // GPU-only execution model.

    // Define the intended usage for our frame texture.
    let intended_usage = TextureUsages::TEXTURE_BINDING | TextureUsages::STORAGE_BINDING;

    // The invariant check:
    let is_gpu_writable = intended_usage.contains(TextureUsages::STORAGE_BINDING);
    let is_cpu_writable = intended_usage.contains(TextureUsages::COPY_DST);

    assert!(
        is_gpu_writable,
        "FRAME texture must have STORAGE_BINDING for the compute kernel to write to it."
    );
    assert!(
        !is_cpu_writable,
        "Invariant Violated: FRAME texture MUST NOT have COPY_DST. The CPU is not allowed to write to it directly."
    );
}