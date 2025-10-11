struct Instr { op:u32, a:u32, b:u32, c:u32 };

@group(0) @binding(0) var<storage, read_write> CODE : array<u32>;
@group(0) @binding(1) var<storage, read_write> STATE: array<u32>;
@group(0) @binding(2) var frame : texture_storage_2d<rgba8unorm, write>;

fn rd4(base:u32, i:u32) -> Instr {
  let p = base + i*4u;
  return Instr(CODE[p], CODE[p+1u], CODE[p+2u], CODE[p+3u]);
}

@compute @workgroup_size(1)
fn exec_ops() {
  var ip = STATE[0];          // instruction pointer (in ops)
  let n  = STATE[1];          // op count available
  while (ip < n) {
    let ins = rd4(0u, ip);
    switch ins.op {
      // PUTPIX x=a, y=b, rgba=c (packed 0xAABBGGRR)
      case 1u: {
        let x = i32(ins.a); let y = i32(ins.b);
        let r = f32((ins.c >>  0) & 255u) / 255.0;
        let g = f32((ins.c >>  8) & 255u) / 255.0;
        let b = f32((ins.c >> 16) & 255u) / 255.0;
        let a = f32((ins.c >> 24) & 255u) / 255.0;
        textureStore(frame, vec2<i32>(x,y), vec4<f32>(r,g,b,a));
      }
      // FILL rect: x=a, y=b, w=(c&0xFFFF), h=(c>>16)
      case 2u: {
        let x = i32(ins.a); let y = i32(ins.b);
        let w = i32(ins.c & 0xFFFFu); let h = i32(ins.c >> 16);
        for (var dy=0; dy<h; dy++) {
          for (var dx=0; dx<w; dx++) {
            textureStore(frame, vec2<i32>(x+dx,y+dy), vec4<f32>(0.95,0.95,0.98,1.0));
          }
        }
      }
      // CURSOR x=a, y=b  (store in STATE)
      case 3u: { STATE[2]=ins.a; STATE[3]=ins.b; }
      default: {}
    }
    ip += 1u;
  }
  STATE[0] = ip;  // persist IP in VRAM
}