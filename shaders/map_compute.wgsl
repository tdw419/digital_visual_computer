// ============================================================================
// GVPIE Map OS - Compute Shader "Kernel" v1.0
// ============================================================================
// Manages all state for the infinite map, including camera, cards, and input.

#import "map_contract.wgsl"

// Main I/O Contract (from original bootstrap)
#import "contract.wgsl"

// ============================================================================
// BINDINGS
// ============================================================================

@group(BINDING_GROUP) @binding(BINDING_STATE) var<storage, read_write> map_state: MapState;
// BINDING_UNIFORMS (1) is used by the render shader.
@group(BINDING_GROUP) @binding(2) var<storage, read> events: array<u32, 256>;
@group(BINDING_GROUP) @binding(3) var<storage, read_write> content_buffer: ContentBuffer;

// ============================================================================
// KERNEL: MAIN
// ============================================================================

@compute @workgroup_size(1)
fn main() {
    if (map_state.camera.zoom == 0.0) {
        init_map();
    }
    process_events();
    update_camera(0.01667); // Assume 60fps
}

// ============================================================================
// INITIALIZATION
// ============================================================================

fn init_map() {
    map_state.camera.zoom = 1.0;
    map_state.camera.target_zoom = 1.0;
    map_state.card_count = 1u;
    map_state.selected_card = -1;
    map_state.hovered_card = -1;
    map_state.dragging_card = -1;

    // Create a welcome card
    map_state.cards[0].x = -200.0;
    map_state.cards[0].y = -100.0;
    map_state.cards[0].width = 400.0;
    map_state.cards[0].height = 200.0;
    map_state.cards[0].color = 0x1A1A2Eff; // Dark Blue
}

// ============================================================================
// CAMERA LOGIC
// ============================================================================

fn update_camera(delta_time: f32) {
    let cam = &map_state.camera;
    (*cam).zoom += ((*cam).target_zoom - (*cam).zoom) * ZOOM_SPEED * delta_time * 0.1;
    (*cam).zoom = clamp((*cam).zoom, ZOOM_MIN, ZOOM_MAX);
    (*cam).target_zoom = clamp((*cam).target_zoom, ZOOM_MIN, ZOOM_MAX);
    (*cam).x += (*cam).velocity_x * delta_time;
    (*cam).y += (*cam).velocity_y * delta_time;
    (*cam).velocity_x *= MOMENTUM_DRAG;
    (*cam).velocity_y *= MOMENTUM_DRAG;
}

fn screen_to_world(screen_x: f32, screen_y: f32, viewport_width: f32, viewport_height: f32) -> vec2<f32> {
    let cam = map_state.camera;
    let ndc_x = (screen_x / viewport_width) * 2.0 - 1.0;
    let ndc_y = 1.0 - (screen_y / viewport_height) * 2.0;
    let world_x = cam.x + (ndc_x * viewport_width / 2.0) / cam.zoom;
    let world_y = cam.y + (ndc_y * viewport_height / 2.0) / cam.zoom;
    return vec2<f32>(world_x, world_y);
}

// ============================================================================
// EVENT PROCESSING
// ============================================================================

fn find_card_at(world_pos: vec2<f32>) -> i32 {
    for (var i = map_state.card_count; i > 0u; i -= 1u) {
        let idx = i - 1u;
        if (point_in_card(map_state.cards[idx], world_pos.x, world_pos.y)) {
            return i32(idx);
        }
    }
    return -1;
}

fn process_events() {
    let event_type = events[0];
    if (event_type == EVENT_NONE) { return; }

    let p1_u = events[1];
    let p2_u = events[2];
    let p1_f = bitcast<f32>(p1_u);
    let p2_f = bitcast<f32>(p2_u);

    switch (event_type) {
        case EVENT_MOUSE_MOVE: {
            let world_pos = screen_to_world(p1_f, p2_f, bitcast<f32>(events[3]), bitcast<f32>(events[4]));
            map_state.mouse_world_x = world_pos.x;
            map_state.mouse_world_y = world_pos.y;
            map_state.hovered_card = find_card_at(world_pos);
            if (map_state.dragging_card != -1) {
                let card = &map_state.cards[u32(map_state.dragging_card)];
                (*card).x = world_pos.x - map_state.drag_offset_x;
                (*card).y = world_pos.y - map_state.drag_offset_y;
            }
        }
        case EVENT_MOUSE_BUTTON: {
            if (p1_u == 0u) { // Left button
                if (p2_u == 1u) { // Pressed
                    if (map_state.hovered_card != -1) {
                        map_state.dragging_card = map_state.hovered_card;
                        map_state.selected_card = map_state.hovered_card;
                        let card = map_state.cards[u32(map_state.dragging_card)];
                        map_state.drag_offset_x = map_state.mouse_world_x - card.x;
                        map_state.drag_offset_y = map_state.mouse_world_y - card.y;
                    } else {
                        map_state.selected_card = -1;
                    }
                } else { // Released
                    map_state.dragging_card = -1;
                }
            }
        }
        case EVENT_SCROLL: {
            map_state.camera.target_zoom *= pow(1.1, -p1_f);
        }
        case EVENT_SPECIAL_KEY: {
            let key = p1_u;
            let pan_amount = PAN_SPEED / map_state.camera.zoom;
            switch (key) {
                case KEY_W: { map_state.camera.velocity_y -= pan_amount; }
                case KEY_A: { map_state.camera.velocity_x -= pan_amount; }
                case KEY_S: { map_state.camera.velocity_y += pan_amount; }
                case KEY_D: { map_state.camera.velocity_x += pan_amount; }
                default: {}
            }
        }
        default: {}
    }

    // Clear event
    let event_ptr = &events[0];
    (*event_ptr) = EVENT_NONE;
}