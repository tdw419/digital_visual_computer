// METADATA:
// Category: Visual State Machines
// Difficulty: Intermediate
// Description: Implements Conway's Game of Life, a classic cellular automaton. The state of each cell is determined by its neighbors, demonstrating a screen-driven computational model.
// Tags: [state machine, cellular automaton, game of life, simulation]

@group(0) @binding(0) var state_texture: texture_2d<f32>;
@group(0) @binding(1) var output_texture: texture_storage_2d<rgba8unorm, write>;

// Function to get the state of a cell, handling boundary conditions.
fn cell_state(x: i32, y: i32) -> u32 {
    let screen_dims = vec2<i32>(textureDimensions(state_texture));
    // Use modulo for wrapping boundary conditions.
    let wrapped_x = (x + screen_dims.x) % screen_dims.x;
    let wrapped_y = (y + screen_dims.y) % screen_dims.y;
    return u32(textureLoad(state_texture, vec2<i32>(wrapped_x, wrapped_y), 0).r);
}

@compute @workgroup_size(8, 8)
fn game_of_life(
    @builtin(global_invocation_id) id: vec3<u32>
) {
    let x = i32(id.x);
    let y = i32(id.y);

    // Count live neighbors.
    var live_neighbors = 0u;
    for (var j = -1; j <= 1; j = j + 1) {
        for (var i = -1; i <= 1; i = i + 1) {
            if (i == 0 && j == 0) {
                continue;
            }
            live_neighbors = live_neighbors + cell_state(x + i, y + j);
        }
    }

    let current_state = cell_state(x, y);
    var next_state = 0.0;

    // Apply the rules of Life.
    if (current_state == 1u) {
        if (live_neighbors == 2u || live_neighbors == 3u) {
            next_state = 1.0;
        }
    } else {
        if (live_neighbors == 3u) {
            next_state = 1.0;
        }
    }

    textureStore(output_texture, id.xy, vec4<f32>(next_state, next_state, next_state, 1.0));
}