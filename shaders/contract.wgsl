// ============================================================================
// GVPIE Canonical I/O Contract - WGSL Mirror
// ============================================================================
// THIS FILE MUST MATCH src/io_contract.rs EXACTLY
// DO NOT EDIT MANUALLY. This should be auto-generated or verified by a script.
// Include in other shaders with: #import "contract.wgsl"

// ============================================================================
// BUFFER LAYOUTS (Must match Rust exactly)
// ============================================================================

struct EditorState {
    text_data: array<u32, 262144>,
    gap_start: u32,
    gap_end: u32,
    total_chars: u32,
    cursor_pos: u32,
    dirty: u32,

    line_offsets: array<u32, 65536>,
    line_count: u32,
    lines_dirty: u32,

    cursor_line: u32,
    cursor_col: u32,
    scroll_offset: u32,  // If >= MODE_3D_THRESHOLD, we are in 3D mode
    selection_start: u32,
    selection_end: u32,
};

struct RenderUniforms {
    time: f32,
    viewport_width: f32,
    viewport_height: f32,
    _padding: f32,
};

// ============================================================================
// EVENT & KEY CODE SYSTEM (Must match Rust exactly)
// ============================================================================

const EVENT_NONE: u32 = 0u;
const EVENT_CHARACTER: u32 = 1u;
const EVENT_SPECIAL_KEY: u32 = 2u;
const EVENT_MOUSE_MOVE: u32 = 3u;
const EVENT_MOUSE_BUTTON: u32 = 4u;
const EVENT_SCROLL: u32 = 5u;

const KEY_BACKSPACE: u32 = 8u;
const KEY_TAB: u32 = 9u;
const KEY_ENTER: u32 = 13u;
const KEY_SHIFT: u32 = 16u;
const KEY_CTRL: u32 = 17u;
const KEY_ALT: u32 = 18u;
const KEY_ESCAPE: u32 = 27u;
const KEY_SPACE: u32 = 32u;
const KEY_LEFT: u32 = 37u;
const KEY_UP: u32 = 38u;
const KEY_RIGHT: u32 = 39u;
const KEY_DOWN: u32 = 40u;
const KEY_DELETE: u32 = 46u;

// Modifier Flags
const MOD_CTRL: u32 = 1u;
const MOD_SHIFT: u32 = 2u;
const MOD_ALT: u32 = 4u;

// ============================================================================
// BINDING LAYOUT (Must match Rust exactly)
// ============================================================================

const BINDING_GROUP: u32 = 0u;
const BINDING_STATE: u32 = 0u;
const BINDING_UNIFORMS: u32 = 1u;
const BINDING_FONT_TEXTURE: u32 = 2u;
const BINDING_FONT_SAMPLER: u32 = 3u;

// ============================================================================
// 3D MODE SYSTEM (Must match Rust exactly)
// ============================================================================

const MODE_3D_THRESHOLD: u32 = 10000u;

fn is_3d_mode(state: EditorState) -> bool {
    return state.scroll_offset >= MODE_3D_THRESHOLD;
}

fn get_scroll_offset_2d(state: EditorState) -> u32 {
    return state.scroll_offset % MODE_3D_THRESHOLD;
}