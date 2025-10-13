//! GVPIE Map OS - Canonical I/O Contract v1.0
//! SINGLE SOURCE OF TRUTH for the 2D Infinite Map system.

use bytemuck::{Pod, Zeroable};

// ============================================================================
// CONSTANTS
// ============================================================================

pub const MAX_CARDS: usize = 4096;
pub const CONTENT_BUFFER_SIZE: usize = 67_108_864; // 256MB for all card content
pub const ZOOM_MIN: f32 = 0.05;
pub const ZOOM_MAX: f32 = 20.0;
pub const PAN_SPEED: f32 = 1000.0;
pub const MOMENTUM_DRAG: f32 = 0.90;

// ============================================================================
// SHARED DATA STRUCTURES
// ============================================================================

#[repr(C)]
#[derive(Copy, Clone, Pod, Zeroable, Debug, Default)]
pub struct Camera {
    pub x: f32,          // World X position of the view's center
    pub y: f32,          // World Y position of the view's center
    pub zoom: f32,       // Current zoom level
    pub target_zoom: f32,// For smooth zooming
    pub velocity_x: f32, // For smooth panning momentum
    pub velocity_y: f32,
}

#[repr(C)]
#[derive(Copy, Clone, Pod, Zeroable, Debug, Default)]
pub struct Card {
    pub x: f32,              // World X position of the card's top-left corner
    pub y: f32,              // World Y position
    pub width: f32,
    pub height: f32,
    pub content_offset: u32,
    pub content_length: u32,
    pub color: u32,          // RGBA packed into a u32
    pub flags: u32,          // Bitfield: 1=selected, 2=hovered, etc.
}

#[repr(C)]
#[derive(Copy, Clone, Pod, Zeroable, Debug)]
pub struct MapState {
    pub camera: Camera,
    pub cards: [Card; MAX_CARDS],
    pub card_count: u32,
    pub selected_card: i32, // Use -1 for none
    pub hovered_card: i32,  // Use -1 for none
    pub dragging_card: i32, // Use -1 for none
    pub drag_offset_x: f32,
    pub drag_offset_y: f32,
    pub mouse_world_x: f32,
    pub mouse_world_y: f32,
    // Padding to ensure alignment and future-proofing
    pub _padding: [u32; 3],
}

// Note: The ContentBuffer is too large to be represented as a single struct
// in Rust's stack/static memory. It will be managed as a raw `wgpu::Buffer`.

// ============================================================================
// VALIDATION LOGIC (for testing)
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_map_struct_sizes() {
        assert_eq!(std::mem::size_of::<Camera>(), 24, "Camera struct size must be 24 bytes!");
        assert_eq!(std::mem::size_of::<Card>(), 32, "Card struct size must be 32 bytes!");

        let map_state_size = std::mem::size_of::<MapState>();
        let expected_map_state_size = 24 + (32 * MAX_CARDS) + 4 + (4 * 3) + (4 * 2) + (4 * 3);
        assert_eq!(map_state_size, expected_map_state_size, "MapState size is incorrect!");
    }
}