// ============================================================================
// EXAMPLE EXTENSION: Word Jumping
// ============================================================================
// This file demonstrates how to add new features to GVPIE by extending the
// WGSL shaders. Copy these functions into your editor_compute.wgsl.

// ----------------------------------------------------------------------------
// 1. DEFINE HELPER FUNCTIONS
// ----------------------------------------------------------------------------

// Determine if a character is a standard word character.
fn is_word_char(ch: u32) -> bool {
    // Alphanumeric
    return (ch >= 48u && ch <= 57u) ||   // 0-9
           (ch >= 65u && ch <= 90u) ||   // A-Z
           (ch >= 97u && ch <= 122u);    // a-z
}

// Determine if a character is whitespace.
fn is_whitespace(ch: u32) -> bool {
    return ch == 32u || ch == 9u || ch == 10u || ch == 13u; // Space, Tab, LF, CR
}

// ----------------------------------------------------------------------------
// 2. IMPLEMENT THE CORE LOGIC
// ----------------------------------------------------------------------------

// Jump cursor forward to the start of the next word.
fn move_cursor_word_forward() {
    let total = state.buffer.total_chars;
    var pos = state.buffer.cursor_pos;

    if (pos >= total) { return; }

    // First, skip any remaining characters of the current word.
    while (pos < total && is_word_char(get_char_at_logical(pos))) {
        pos = pos + 1u;
    }

    // Then, skip any whitespace to find the start of the next word.
    while (pos < total && is_whitespace(get_char_at_logical(pos))) {
        pos = pos + 1u;
    }

    set_cursor_pos(pos);
}

// Jump cursor backward to the start of the previous word.
fn move_cursor_word_backward() {
    var pos = state.buffer.cursor_pos;

    if (pos == 0u) { return; }

    // Move back one character to start.
    pos = pos - 1u;

    // First, skip any whitespace.
    while (pos > 0u && is_whitespace(get_char_at_logical(pos))) {
        pos = pos - 1u;
    }

    // Then, skip backward over the word characters to find its start.
    while (pos > 0u && is_word_char(get_char_at_logical(pos - 1u))) {
        pos = pos - 1u;
    }

    set_cursor_pos(pos);
}


// ----------------------------------------------------------------------------
// 3. INTEGRATE INTO THE KEYBINDING HANDLER
// ----------------------------------------------------------------------------

// Modify your `handle_special_key` function to check for the Ctrl modifier.
fn handle_special_key(key: u32, mods: u32) {
    let is_ctrl = (mods & 1u) != 0u;

    switch (key) {
        case 37u: { // Left arrow
            if (is_ctrl) {
                move_cursor_word_backward();
            } else {
                move_cursor_left();
            }
        }
        case 39u: { // Right arrow
            if (is_ctrl) {
                move_cursor_word_forward();
            } else {
                move_cursor_right();
            }
        }
        // ... other cases for Backspace, Delete, Up, Down, etc.
        default: {}
    }
}

// ----------------------------------------------------------------------------
// DEVELOPMENT PATTERNS TO LEARN FROM THIS EXAMPLE
// ----------------------------------------------------------------------------
//
// 1.  **Pure Helper Functions**: `is_word_char` and `is_whitespace` are simple,
//     testable, and make the main logic easier to read.
//
// 2.  **Stateful Main Logic**: `move_cursor_word_forward` reads from the
//     global `state` buffer and calls other functions that modify it.
//
// 3.  **Single Point of Entry**: All logic is triggered from the keybinding
//     handler, which checks for modifier keys.
//
// 4.  **Incremental Enhancement**: We didn't rewrite `move_cursor_left`; we
//     added a new code path that is conditionally executed.
//
// Use these patterns when building your own features!