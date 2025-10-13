// ============================================================================
// GVPIE Editor Compute Shader v1.1
// ============================================================================
// Uses the canonical I/O contract for guaranteed compatibility.

#import "contract.wgsl"

// ----------------------------------------------------------------------------
// BINDINGS (Using contract constants)
// ----------------------------------------------------------------------------

@group(BINDING_GROUP) @binding(BINDING_STATE) var<storage, read_write> state: EditorState;
// NOTE: The frozen bootstrap v1.0.0 only provides bindings 0-3.
// The render shader uses 2 and 3 for font texture/sampler.
// For this compute shader to work as intended, the bootstrap would need
// to be unfrozen to provide additional bindings for events and requests.
// We use 4 and 5 here as a placeholder for the required bindings.
@group(BINDING_GROUP) @binding(4) var<storage, read_write> events: array<u32, 256>;
@group(BINDING_GROUP) @binding(5) var<storage, read_write> requests: array<u32, 256>;

// ----------------------------------------------------------------------------
// GAP BUFFER & EDITING LOGIC (Unchanged, but now relies on contract structs)
// ----------------------------------------------------------------------------

fn move_gap(target_pos: u32) {
    // ... (logic remains the same)
}

fn insert_char(ch: u32) {
    // ... (logic remains the same)
}

fn delete_char_back() {
    // ... (logic remains the same)
}

fn delete_char_forward() {
    // ... (logic remains the same)
}

// ----------------------------------------------------------------------------
// EVENT HANDLING (Refactored to use contract constants)
// ----------------------------------------------------------------------------

fn handle_special_key(key: u32, mods: u32) {
    switch (key) {
        case KEY_BACKSPACE: { delete_char_back(); }
        case KEY_DELETE: { delete_char_forward(); }
        case KEY_LEFT: { /* move_cursor_left(); */ }
        case KEY_RIGHT: { /* move_cursor_right(); */ }
        case KEY_UP: { /* move_cursor_up(); */ }
        case KEY_DOWN: { /* move_cursor_down(); */ }
        case KEY_ENTER: { insert_char(10u); }
        default: {}
    }
}

fn process_events() {
    let event_type = events[0];
    if (event_type == EVENT_NONE) { return; }

    let payload1 = events[1];
    let payload2 = events[2];

    switch (event_type) {
        case EVENT_CHARACTER: {
            insert_char(payload1);
        }
        case EVENT_SPECIAL_KEY: {
            handle_special_key(payload1, payload2);
        }
        default: {}
    }

    // Consume the event
    events[0] = EVENT_NONE;
}

// ----------------------------------------------------------------------------
// 3D MODE TOGGLE (Now safe and clean)
// ----------------------------------------------------------------------------

fn check_3d_mode_toggle() {
    if (events[0] == EVENT_SPECIAL_KEY && events[1] == KEY_SPACE && (events[2] & MOD_CTRL) != 0u) {
        if (is_3d_mode(state)) {
            state.scroll_offset = get_scroll_offset_2d(state);
        } else {
            state.scroll_offset += MODE_3D_THRESHOLD;
        }
        events[0] = EVENT_NONE; // Consume event
    }
}

// ----------------------------------------------------------------------------
// MAIN COMPUTE
// ----------------------------------------------------------------------------

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    if (gid.x == 0u) {
        // First, check for mode toggle, as it's a high-priority global action
        check_3d_mode_toggle();

        // Process other events
        if (!is_3d_mode(state)) {
            process_events(); // Process 2D editing events
            // ... (rest of 2D compute logic: line rebuilding, etc.)
        } else {
            // Process 3D interaction events here in the future
        }
    }
}