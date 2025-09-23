// A minimal, verifiable edit kernel for the MVP.

// The character buffer, storing u32 character codes.
@group(0) @binding(0) var<storage, read_write> buf_chars: array<u32>;

// Uniforms to control the operation.
struct Uniforms {
    opcode: u32,      // 1 for INS_CHAR, 2 for BKSP
    char_code: u32,   // The character to insert
    cursor_pos: u32,  // The position to insert/delete at
};
@group(0) @binding(1) var<uniform> uniforms: Uniforms;

// A simple shift-right implementation to make space for a new character.
fn shift_right(start_index: u32) {
    // Start from the end of the buffer and move everything one position to the right.
    // This is inefficient, but simple and verifiable for the MVP.
    for (var i: u32 = arrayLength(&buf_chars) - 1u; i > start_index; i = i - 1u) {
        buf_chars[i] = buf_chars[i - 1u];
    }
}

// A simple shift-left implementation to fill the gap after a deletion.
fn shift_left(start_index: u32) {
    for (var i: u32 = start_index; i < arrayLength(&buf_chars) - 1u; i = i + 1u) {
        buf_chars[i] = buf_chars[i + 1u];
    }
    // Clear the last element
    buf_chars[arrayLength(&buf_chars) - 1u] = 0u;
}

@compute @workgroup_size(1)
fn main() {
    if (uniforms.opcode == 1u) { // INS_CHAR
        shift_right(uniforms.cursor_pos);
        buf_chars[uniforms.cursor_pos] = uniforms.char_code;
    } else if (uniforms.opcode == 2u) { // BKSP
        if (uniforms.cursor_pos > 0u) {
            shift_left(uniforms.cursor_pos - 1u);
        }
    }
}
