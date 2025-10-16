#include "hv_common.wgsl"
#include "hv_mem.wgsl"

// super-simple blit: one texel per character cell
// white if char != 0, black otherwise
@compute @workgroup_size(8,8,1)
fn hv_console_blt(@builtin(global_invocation_id) gid:vec3<u32>){
  let x = gid.x;
  let y = gid.y;
  if (x >= io_header.cols || y >= io_header.rows) { return; }

  let idx = y * io_header.cols + x;
  let ch = ld8(hv_state.console_base + idx);

  let color = select(vec4<f32>(0.0,0.0,0.0,1.0),
                     vec4<f32>(1.0,1.0,1.0,1.0),
                     ch != 0u);

  textureStore(console_tex, vec2<i32>(i32(x), i32(y)), color);
}