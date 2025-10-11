struct Instr { op:u32, a:u32, b:u32, c:u32 };

@group(0) @binding(0) var<storage, read> TEXT : array<u32>;
@group(0) @binding(1) var<storage, read_write> CODE : array<u32>;
@group(0) @binding(2) var<storage, read_write> STATE: array<u32>;

fn wr4(base:u32, i:u32, ins:Instr) {
  let p = base + i*4u;
  CODE[p]=ins.op; CODE[p+1u]=ins.a; CODE[p+2u]=ins.b; CODE[p+3u]=ins.c;
}

@compute @workgroup_size(64)
fn parse_text_to_ops(@builtin(global_invocation_id) gid:vec3<u32>) {
  let i = gid.x;
  let text_len = STATE[5]; // state[5] = text_len
  if (i >= text_len) { return; }

  let ch = TEXT[i]; // utf-32
  if (ch == 0u) { return; }

  // toy language: 'Xxy' draws a white pixel at (x,y) where x=next char, y=next char
  if (ch == 88u) { // 'X'
    if (i + 2 >= text_len) { return; } // Bounds check
    let x = TEXT[i+1u];
    let y = TEXT[i+2u];
    let idx = atomicAdd(&STATE[1], 1u); // STATE[1] = op_count
    wr4(0u, idx, Instr(1u, x, y, 0xFFFFFFFFu)); // PUTPIX
  }
  // Add more parsing rules here in the future
}