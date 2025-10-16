// METADATA:
// Category: Data Encoding
// Difficulty: Beginner
// Description: Decodes a 32-bit floating-point number from a vec4<f32> color that was previously encoded using an 8-bit-per-channel scheme. This is essential for reading high-precision data from textures.
// Tags: [decoding, float, color, texture, data]

// Decodes a vec4<f32> color back into a 32-bit float.
fn decode_color_as_float(color: vec4<f32>) -> f32 {
    let bits = (u32(color.r * 255.0) << 24) |
              (u32(color.g * 255.0) << 16) |
              (u32(color.b * 255.0) << 8) |
              u32(color.a * 255.0);
    return bitcast<f32>(bits);
}