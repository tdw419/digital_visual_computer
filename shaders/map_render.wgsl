// ============================================================================
// GVPIE Map OS - Render Shader v1.0
// ============================================================================
// Renders the infinite grid, cards, and text content procedurally.

#import "map_contract.wgsl"
#import "contract.wgsl"

// ============================================================================
// BINDINGS
// ============================================================================

@group(BINDING_GROUP) @binding(BINDING_STATE) var<storage, read> map_state: MapState;
@group(BINDING_GROUP) @binding(BINDING_UNIFORMS) var<uniform> uniforms: RenderUniforms;
@group(BINDING_GROUP) @binding(BINDING_FONT_TEXTURE) var font_texture: texture_2d<f32>;
@group(BINDING_GROUP) @binding(BINDING_FONT_SAMPLER) var font_sampler: sampler;
@group(BINDING_GROUP) @binding(3) var<storage, read> content_buffer: ContentBuffer; // Re-using binding 3

// ============================================================================
// DATA STRUCTURES
// ============================================================================

struct VertexOutput {
    @builtin(position) position: vec4<f32>,
    @location(0) color: vec4<f32>,
    @location(1) tex_coord: vec2<f32>,
    @location(2) entity_type: u32, // 0: Grid, 1: Card, 2: Text
};

// ============================================================================
// KERNEL: VERTEX SHADER (Uber-shader approach)
// ============================================================================

@vertex
fn vs_main(@builtin(vertex_index) vid: u32) -> VertexOutput {
    // We use one large draw call and use the vertex index to decide what to draw.
    // This is a common technique for simple, GPU-driven renderers.

    // First, render cards (4 vertices per card)
    let card_vertex_count = MAX_CARDS * 4u;
    if (vid < card_vertex_count) {
        return vs_card(vid);
    }

    // Then, render text. This is a simplified calculation for the number of vertices.
    // A real implementation would need to know the total number of characters.
    let text_vertex_count = card_vertex_count + 1000 * 6u; // Assume max 1000 chars for now
    if (vid < text_vertex_count) {
        return vs_text(vid - card_vertex_count);
    }

    // Finally, render the grid using a full-screen triangle
    let grid_vid = vid - text_vertex_count;
    let positions = array<vec2<f32>, 3>(
        vec2<f32>(-1.0, -1.0), vec2<f32>(3.0, -1.0), vec2<f32>(-1.0, 3.0)
    );
    if (grid_vid < 3u) {
        return VertexOutput(vec4<f32>(positions[grid_vid], 0.99, 1.0), vec4f(0.0), vec2f(0.0), 0u);
    }

    // Return a degenerate triangle if vid is out of bounds
    return VertexOutput(vec4f(0.0), vec4f(0.0), vec2f(0.0), 0u);
}

fn vs_card(vid: u32) -> VertexOutput {
    let card_index = vid / 4u;
    let corner_index = vid % 4u;

    if (card_index >= map_state.card_count) {
        return VertexOutput(vec4f(0.0), vec4f(0.0), vec2f(0.0), 1u);
    }

    let card = map_state.cards[card_index];
    var corner_pos: vec2<f32>;
    switch (corner_index) {
        case 0u: { corner_pos = vec2<f32>(card.x, card.y); }
        case 1u: { corner_pos = vec2<f32>(card.x + card.width, card.y); }
        case 2u: { corner_pos = vec2<f32>(card.x, card.y + card.height); }
        case 3u: { corner_pos = vec2<f32>(card.x + card.width, card.y + card.height); }
        default: { corner_pos = vec2<f32>(0.0); }
    }

    let screen_pos = world_to_screen(corner_pos);
    let ndc_pos = screen_to_ndc(screen_pos);

    var color = unpack_color(card.color);
    if (i32(card_index) == map_state.hovered_card) { color *= 1.2; }
    if (i32(card_index) == map_state.selected_card) { color.b = min(1.0, color.b + 0.3); }

    return VertexOutput(vec4<f32>(ndc_pos, 0.5, 1.0), color, vec2f(0.0), 1u);
}

// ============================================================================
// KERNEL: FRAGMENT SHADER
// ============================================================================

@fragment
fn fs_main(input: VertexOutput) -> @location(0) vec4<f32> {
    switch (input.entity_type) {
        case 0u: { return fs_grid(input.position.xy); }
        case 1u: { return input.color; }
        case 2u: {
            let glyph = textureSample(font_texture, font_sampler, input.tex_coord);
            if (glyph.a < 0.1) {
                discard;
            }
            return glyph * input.color;
        }
        default: { return vec4f(1.0, 0.0, 1.0, 1.0); } // Magenta for errors
    }
}

fn vs_text(vid: u32) -> VertexOutput {
    let char_instance_index = vid / 6u;
    let vertex_in_quad = vid % 6u;

    // This is a placeholder to find the correct character and card.
    // A robust implementation would use another buffer to map char_instance_index
    // to a specific card and character offset. For now, we only render text for card 0.
    if (char_instance_index >= map_state.cards[0].content_length) {
        return VertexOutput(vec4f(0.0), vec4f(0.0), vec2f(0.0), 2u);
    }

    let card = map_state.cards[0];
    let char_code = content_buffer.data[card.content_offset + char_instance_index];

    let char_col = char_instance_index % u32(card.width / 9.0);
    let char_row = char_instance_index / u32(card.width / 9.0);

    let char_world_pos = vec2<f32>(
        card.x + 10.0 + f32(char_col) * 9.0, // 10px padding
        card.y + 30.0 + f32(char_row) * 16.0 // 30px for title
    );

    let quad_positions = array<vec2<f32>, 6>(
        vec2(0.0, 0.0), vec2(9.0, 0.0), vec2(0.0, 16.0),
        vec2(0.0, 16.0), vec2(9.0, 0.0), vec2(9.0, 16.0)
    );
    let quad_uvs = array<vec2<f32>, 6>(
        vec2(0.0, 0.0), vec2(1.0, 0.0), vec2(0.0, 1.0),
        vec2(0.0, 1.0), vec2(1.0, 0.0), vec2(1.0, 1.0)
    );

    let world_pos = char_world_pos + quad_positions[vertex_in_quad];
    let screen_pos = world_to_screen(world_pos);
    let ndc_pos = screen_to_ndc(screen_pos);

    let atlas_col = f32(char_code % 16u);
    let atlas_row = f32(char_code / 16u);
    let atlas_cell_size = 1.0 / 16.0;
    let tex_coord = vec2<f32>(
        (atlas_col + quad_uvs[vertex_in_quad].x) * atlas_cell_size,
        (atlas_row + quad_uvs[vertex_in_quad].y) * atlas_cell_size
    );

    return VertexOutput(vec4<f32>(ndc_pos, 0.4, 1.0), vec4f(1.0, 1.0, 1.0, 1.0), tex_coord, 2u);
}

fn fs_grid(frag_coord: vec2<f32>) -> vec4<f32> {
    let world_pos = screen_to_world(frag_coord);

    let grid_major_spacing = 100.0;
    let grid_minor_spacing = 20.0;
    let line_width = 0.8 * map_state.camera.zoom;

    let major_grid = abs(mod(world_pos, grid_major_spacing));
    let minor_grid = abs(mod(world_pos, grid_minor_spacing));

    let major_alpha = 1.0 - min(smoothstep(line_width, 0.0, major_grid.x), smoothstep(line_width, 0.0, major_grid.y));
    let minor_alpha = 1.0 - min(smoothstep(line_width, 0.0, minor_grid.x), smoothstep(line_width, 0.0, minor_grid.y));

    let base_color = vec4<f32>(0.15, 0.15, 0.18, 1.0);
    let minor_color = mix(base_color, vec4f(0.2, 0.2, 0.25, 1.0), minor_alpha);
    return mix(minor_color, vec4f(0.3, 0.3, 0.35, 1.0), major_alpha);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

fn world_to_screen(world_pos: vec2<f32>) -> vec2<f32> {
    let cam = map_state.camera;
    let view_pos = (world_pos - vec2<f32>(cam.x, cam.y)) * cam.zoom;
    return view_pos + vec2<f32>(uniforms.viewport_width / 2.0, uniforms.viewport_height / 2.0);
}

fn screen_to_ndc(screen_pos: vec2<f32>) -> vec2<f32> {
    let ndc_x = (screen_pos.x / uniforms.viewport_width) * 2.0 - 1.0;
    let ndc_y = (screen_pos.y / uniforms.viewport_height) * 2.0 - 1.0;
    return vec2<f32>(ndc_x, -ndc_y);
}

fn screen_to_world(frag_coord: vec2<f32>) -> vec2<f32> {
    let cam = map_state.camera;
    let ndc = vec2<f32>(
        (frag_coord.x / uniforms.viewport_width) * 2.0 - 1.0,
        (1.0 - (frag_coord.y / uniforms.viewport_height)) * 2.0 - 1.0
    );
    let world_x = cam.x + (ndc.x * uniforms.viewport_width / 2.0) / cam.zoom;
    let world_y = cam.y + (ndc.y * uniforms.viewport_height / 2.0) / cam.zoom;
    return vec2<f32>(world_x, world_y);
}