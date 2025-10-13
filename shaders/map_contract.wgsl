// ============================================================================
// GVPIE Map OS - Canonical I/O Contract v1.0 - WGSL Mirror
// ============================================================================
// THIS FILE MUST MATCH src/map_io_contract.rs EXACTLY.

// ============================================================================
// CONSTANTS
// ============================================================================

const MAX_CARDS: u32 = 4096u;
const ZOOM_MIN: f32 = 0.05;
const ZOOM_MAX: f32 = 20.0;
const PAN_SPEED: f32 = 1000.0;
const MOMENTUM_DRAG: f32 = 0.90;

// ============================================================================
// SHARED DATA STRUCTURES
// ============================================================================

struct Camera {
    x: f32,
    y: f32,
    zoom: f32,
    target_zoom: f32,
    velocity_x: f32,
    velocity_y: f32,
};

struct Card {
    x: f32,
    y: f32,
    width: f32,
    height: f32,
    content_offset: u32,
    content_length: u32,
    color: u32,
    flags: u32,
};

struct MapState {
    camera: Camera,
    cards: array<Card, MAX_CARDS>,
    card_count: u32,
    selected_card: i32,
    hovered_card: i32,
    dragging_card: i32,
    drag_offset_x: f32,
    drag_offset_y: f32,
    mouse_world_x: f32,
    mouse_world_y: f32,
    _padding: array<u32, 3>,
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

fn unpack_color(packed: u32) -> vec4<f32> {
    let r = f32((packed >> 24u) & 0xFFu) / 255.0;
    let g = f32((packed >> 16u) & 0xFFu) / 255.0;
    let b = f32((packed >> 8u) & 0xFFu) / 255.0;
    let a = f32(packed & 0xFFu) / 255.0;
    return vec4<f32>(r, g, b, a);
}

fn point_in_card(card: Card, world_x: f32, world_y: f32) -> bool {
    return world_x >= card.x &&
           world_x <= card.x + card.width &&
           world_y >= card.y &&
           world_y <= card.y + card.height;
}

// Flags for card state
const FLAG_SELECTED: u32 = 1u;
const FLAG_HOVERED: u32 = 2u;
const FLAG_DRAGGING: u32 = 4u;