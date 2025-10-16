// METADATA:
// Category: Data Encoding
// Difficulty: Beginner
// Description: Encodes a 32-bit floating-point number into the four 8-bit channels of a vec4<f32> color. This is a fundamental technique for storing high-precision data in standard RGBA textures.
// Tags: [encoding, float, color, texture, data]

// Encodes a 32-bit float into a vec4<f32> suitable for storing in an RGBA8 texture.
fn encode_float_as_color(value: f32) -> vec4<f32> {
    let bits = bitcast<u32>(value);
    return vec4<f32>(
        f32((bits >> 24) & 0xFFu) / 255.0,
        f32((bits >> 16) & 0xFFu) / 255.0,
        f32((bits >> 8) & 0xFFu) / 255.0,
        f32(bits & 0xFFu) / 255.0
    );
}