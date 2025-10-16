struct Regs {
    head: atomic<u32>,
    tail: atomic<u32>,
    cap_pow2: u32,
    err: atomic<u32>,
    cppm_accumulator: atomic<u32>,
    active_pixel_count: atomic<u32>,
    cppm_budget: u32,
    _padding1: u32,
};

@group(0) @binding(0) var<storage, read_write> regs: Regs;
struct Command {
    op_flags: u32,
    params1: u32, // a: u16, b: u16
    params2: u32, // c: u16, d: u16
    params3: u32, // v0: u16, v1: u16
};

@group(0) @binding(1) var<storage, read_write> cmdq: array<Command>;
@group(0) @binding(2) var<storage, read> inbox_ascii: array<u32>;

fn char_to_nibble(char_code: u32) -> i32 {
    if (char_code >= 48u && char_code <= 57u) { // '0' - '9'
        return i32(char_code - 48u);
    }
    if (char_code >= 97u && char_code <= 102u) { // 'a' - 'f'
        return i32(char_code - 87u);
    }
    if (char_code >= 65u && char_code <= 70u) { // 'A' - 'F'
        return i32(char_code - 55u);
    }
    return -1; // Invalid hex char
}

@group(0) @binding(3) var workTex: texture_storage_2d<rgba8uint, write>;

// --- PCM-8 Command Executor ---
@compute @workgroup_size(1)
fn exec() {
  var steps = 0u;
  loop {
    let current_tail = atomicLoad(&regs.tail);
    let current_head = atomicLoad(&regs.head);
    if (current_tail >= current_head || steps >= 4096u) {
        break;
    }
    let idx = (current_tail & (regs.cap_pow2 - 1u));
    let cmd = cmdq[idx];

    let op = cmd.op_flags & 0xFFu;
    let a  = cmd.params1 & 0xFFFFu;
    let b  = (cmd.params1 >> 16u) & 0xFFFFu;
    let c  = cmd.params2 & 0xFFFFu;
    let d  = (cmd.params2 >> 16u) & 0xFFFFu;
    let v0 = cmd.params3 & 0xFFFFu;

    switch op {
        case 0x10u: { // PLOT
            textureStore(workTex, vec2<i32>(i32(a), i32(b)), vec4<u32>(v0 & 0xFFu, 0u, 0u, 255u));
            atomicAdd(&regs.active_pixel_count, 1u);
            atomicAdd(&regs.cppm_accumulator, 1u);
        }
        case 0x11u: { // RECT
            for (var yy: u32 = 0u; yy < d; yy = yy + 1u) {
                for (var xx: u32 = 0u; xx < c; xx = xx + 1u) {
                    textureStore(workTex, vec2<i32>(i32(a + xx), i32(b + yy)), vec4<u32>(v0 & 0xFFu, 0u, 0u, 255u));
                }
            }
            let pixel_count = c * d;
            atomicAdd(&regs.active_pixel_count, pixel_count);
            atomicAdd(&regs.cppm_accumulator, pixel_count);
        }
        case 0x07u: { // CPPM_READ
            let val = atomicLoad(&regs.cppm_accumulator);
            // Simulate writing to a register/memory by writing to the error register for now.
            atomicStore(&regs.err, val);
        }
        default: {
            atomicStore(&regs.err, op);
        }
    }

    atomicAdd(&regs.tail, 1u);
    steps += 1u;
  }
}

// --- ASCII to CMDQ Parser ---
@compute @workgroup_size(1)
fn parse() {
    var inbox_ptr = 0u;
    var byte_buffer: array<u32, 16>;
    var byte_count = 0u;
    var high_nibble = true;
    var current_byte = 0u;

    loop {
        if (inbox_ptr >= arrayLength(&inbox_ascii)) {
            break;
        }

        let char_code = inbox_ascii[inbox_ptr];
        inbox_ptr += 1u;

        if (char_code == 32u || char_code == 10u || char_code == 13u || char_code == 9u) { // Whitespace
            continue;
        }

        if (char_code == 59u) { // ';' comment
            loop {
                if (inbox_ptr >= arrayLength(&inbox_ascii) || inbox_ascii[inbox_ptr] == 10u) {
                    break;
                }
                inbox_ptr += 1u;
            }
            continue;
        }

        let nibble = char_to_nibble(char_code);
        if (nibble < 0) {
            regs.err = 1u; // Set error flag
            return;
        }

        if (high_nibble) {
            current_byte = u32(nibble) << 4u;
        } else {
            current_byte = current_byte | u32(nibble);
            byte_buffer[byte_count] = u32(current_byte);
            byte_count += 1u;
        }
        high_nibble = !high_nibble;

        if (byte_count == 16u) {
            // Write the 16-byte command to the CMDQ
            let cmd_idx = regs.head & (regs.cap_pow2 - 1u);
            cmdq[cmd_idx].op_flags = byte_buffer[0] | (byte_buffer[1] << 8u) | (byte_buffer[2] << 16u) | (byte_buffer[3] << 24u);
            cmdq[cmd_idx].params1 = byte_buffer[4] | (byte_buffer[5] << 8u) | (byte_buffer[6] << 16u) | (byte_buffer[7] << 24u);
            cmdq[cmd_idx].params2 = byte_buffer[8] | (byte_buffer[9] << 8u) | (byte_buffer[10] << 16u) | (byte_buffer[11] << 24u);
            cmdq[cmd_idx].params3 = byte_buffer[12] | (byte_buffer[13] << 8u) | (byte_buffer[14] << 16u) | (byte_buffer[15] << 24u);

            atomicAdd(&regs.head, 1u);
            byte_count = 0u;
        }
    }
}