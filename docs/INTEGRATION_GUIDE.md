# GVPIE Text Engine Integration Guide

## What We Built

**`editor_compute.wgsl`** - A complete gap buffer text engine with:
- Efficient O(1) insertion/deletion at cursor
- Line indexing for O(log n) line lookups
- Cursor movement (char/line navigation)
- UTF-32 character storage (~260k chars)
- Event processing from host

**`editor_render.wgsl`** - Procedural text rendering with:
- Instance-based character rendering (no VBOs)
- Viewport scrolling
- Blinking cursor
- Font atlas texture mapping

## Integration Steps

### 1. Update Your Shader References

Ensure your Rust bootstrap loads these two files:
- `shaders/editor_compute.wgsl` for the compute pipeline.
- `shaders/editor_render.wgsl` for the render pipeline.

### 2. Verify Buffer Layouts

The WGSL shaders expect the following bind group layouts. Your Rust code must match these bindings.

**Compute Pipeline (`@group(0)`):**
| Binding | Type            | Size        | Usage (WGSL)                     |
|---------|-----------------|-------------|----------------------------------|
| `0`     | `storage`       | `~5MB`      | `var<storage, read_write> state` |
| `1`     | `storage`       | `4KB`       | `var<storage, read> events`      |
| `2`     | `storage`       | `1KB`       | `var<storage, read_write> requests`|

**Render Pipeline (`@group(0)`):**
| Binding | Type            | Size        | Usage (WGSL)                     |
|---------|-----------------|-------------|----------------------------------|
| `0`     | `storage`       | `~5MB`      | `var<storage, read> state`       |
| `1`     | `uniform`       | `16 bytes`  | `var<uniform> uniforms`          |
| `2`     | `texture_2d`    | `~37KB`     | `var font_texture`               |
| `3`     | `sampler`       | -           | `var font_sampler`               |

### 3. Implement the Event Format

The compute shader consumes events from the `events` buffer. Your Rust event loop must write to this buffer using the following format before each compute pass.

- `events[0]`: **Event Type**. `0`=None, `1`=Character Input, `2`=Special Key.
- `events[1]`: **Key Code**. For characters, the UTF-32 code point. For special keys, the virtual key code.
- `events[2]`: **Modifiers**. A bitfield: `Ctrl=1`, `Shift=2`, `Alt=4`.

After writing an event, the shader expects the host to do nothing; the shader itself will reset `events[0]` to `0` after consumption.

### 4. Add the Render Uniform Buffer

The render shader requires a uniform buffer with timing and viewport information.

```rust
// In your Rust code
#[repr(C)]
#[derive(Copy, Clone, bytemuck::Pod, bytemuck::Zeroable)]
struct RenderUniforms {
    time: f32,
    viewport_width: f32,
    viewport_height: f32,
    _padding: f32,
}
```
You must create a `wgpu::Buffer` for these uniforms and update it every frame with the elapsed time and the current window dimensions.

### 5. Create a Font Atlas

The render shader requires a 256-character font atlas, laid out as a 16x16 grid.
- **Texture Size**: Depends on character cell size. For 9x16 pixel characters, the texture would be `(16*9) x (16*16) = 144x256` pixels.
- **Format**: `wgpu::TextureFormat::Rgba8UnormSrgb` is recommended.
- **Generation**: You can generate this texture procedurally at startup or load it from a pre-made image file (e.g., a `.png`). For testing, a simple bitmap font is sufficient.

### 6. Set Up the Render Pipeline

Your render pipeline should be configured for instanced drawing. You will make two draw calls:

1.  **Draw Text**:
    - Call `draw()` with `0..4` vertices (for a quad) and `0..num_visible_chars` instances. `num_visible_chars` is `(viewport_width / char_width) * (viewport_height / char_height)`.
    - Use the `vs_main` and `fs_main` entry points.

2.  **Draw Cursor**:
    - Call `draw()` with `0..4` vertices and `0..1` instances.
    - Use the `vs_cursor` and `fs_cursor` entry points. This should be a separate pipeline state object or a re-configured pass.

## Testing the Integration

1.  **Run `cargo run --release`**. You should see an empty window with a blinking cursor at the top-left.
2.  **Type characters**. They should appear on the screen, and the cursor should advance.
3.  **Use arrow keys**. The cursor should navigate the text.
4.  **Press Backspace and Delete**. Characters should be removed correctly.

## Troubleshooting

- **No text appears**:
    - Check that the `state` buffer is correctly bound in the render pipeline.
    - Verify your font atlas texture and sampler are correct.
    - Ensure `num_visible_chars` is greater than zero.
- **Cursor doesn't blink**:
    - Make sure the `time` uniform is being updated every frame.
- **Input doesn't work**:
    - Double-check that your Rust event loop is writing to the `events` buffer in the correct format.
    - Confirm the `events` buffer is correctly bound in the compute pipeline.

## Next Steps

Once this foundation is working, you can begin extending the editor's functionality by modifying the WGSL shaders. The `ROADMAP.md` provides a structured plan for adding features like:
- Word jumping
- Selection
- File I/O
- Undo/redo
- Syntax highlighting

All future development occurs in the shaders. The Rust bootstrap is frozen. Welcome to GPU Sovereignty.