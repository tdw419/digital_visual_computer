// METADATA:
// Category: Pixel Data Analysis
// Difficulty: Beginner
// Description: Analyzes the luminance of screen pixels and uses the result to drive a subsequent computation. This demonstrates the core principle of screen-driven computing.
// Tags: [analysis, pixel, luminance, screen-driven]

@group(0) @binding(0) var screen_texture: texture_2d<f32>;
@group(0) @binding(1) var<storage, read_write> output_buffer: array<f32>;

@compute @workgroup_size(16, 16)
fn luminance_analyzer(
    @builtin(global_invocation_id) id: vec3<u32>
) {
    let pixel_coord = vec2<i32>(i32(id.x), i32(id.y));
    let screen_data = textureLoad(screen_texture, pixel_coord, 0);

    // Extract luminance as a computational input.
    // This uses the standard NTSC luminance formula.
    let luminance = dot(screen_data.rgb, vec3<f32>(0.299, 0.587, 0.114));

    // Use luminance to drive a computation.
    // Example: A simple scaling operation.
    let computation_result = luminance * 100.0;

    // A more complex example could be adjusting simulation parameters,
    // setting the intensity of a light source, or controlling the
    // behavior of an AI agent based on what it "sees".

    let output_index = id.y * 1024u + id.x; // Assuming a 1024x1024 texture
    output_buffer[output_index] = computation_result;
}