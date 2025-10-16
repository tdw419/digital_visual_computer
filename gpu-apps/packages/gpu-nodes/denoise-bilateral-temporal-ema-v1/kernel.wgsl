// Bilateral filter followed by temporal EMA in a single pass.
// Ping-pong by writing both denoised_out and next_prev_tex the same value.

struct DenoiseParams {
  size: vec2<u32>,
  sigma_s: f32,   // spatial sigma (pixels)
  sigma_r: f32,   // range sigma (0..1)
  alpha: f32      // EMA blend (0..1), 0=stick to prev, 1=trust current
};

@group(0) @binding(0) var<uniform> U: DenoiseParams;
@group(0) @binding(1) var src_tex: texture_2d<f32>;
@group(0) @binding(2) var prev_tex: texture_2d<f32>;
@group(0) @binding(3) var out_tex: texture_storage_2d<rgba8unorm, write>;
@group(0) @binding(4) var out_next_prev: texture_storage_2d<rgba8unorm, write>;

fn clampCoord(p: vec2<i32>, wh: vec2<i32>) -> vec2<i32> {
  return clamp(p, vec2<i32>(0,0), wh - vec2<i32>(1,1));
}

fn luma(c: vec3<f32>) -> f32 { return dot(c, vec3<f32>(0.299, 0.587, 0.114)); }

@compute @workgroup_size(16,16)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  if (any(gid.xy >= U.size)) { return; }
  let wh_i = vec2<i32>(i32(U.size.x), i32(U.size.y));
  let p = vec2<i32>(i32(gid.x), i32(gid.y));

  // --- Bilateral ---
  let center = textureLoad(src_tex, p, 0).rgb;
  let center_y = luma(center);
  let r = u32(ceil(2.0 * max(U.sigma_s, 0.5)));
  var num = vec3<f32>(0.0);
  var den = 0.0;
  for (var dy: i32 = -i32(r); dy <= i32(r); dy++) {
    for (var dx: i32 = -i32(r); dx <= i32(r); dx++) {
      let q = clampCoord(p + vec2<i32>(dx,dy), wh_i);
      let s = textureLoad(src_tex, q, 0).rgb;
      let sd = length(vec2<f32>(f32(dx), f32(dy)));
      let wd = exp(-0.5 * (sd*sd) / max(U.sigma_s*U.sigma_s, 1e-5));
      let rd = center_y - luma(s);
      let wr = exp(-0.5 * (rd*rd) / max(U.sigma_r*U.sigma_r, 1e-6));
      let w = wd * wr;
      num += s * w;
      den += w;
    }
  }
  let bilateral_rgb = select(center, num / max(den, 1e-6), den > 0.0);

  // --- Temporal EMA ---
  let prev_rgb = textureLoad(prev_tex, p, 0).rgb;
  let a = clamp(U.alpha, 0.0, 1.0);
  let ema_rgb = mix(prev_rgb, bilateral_rgb, a);
  let out_px = vec4<f32>(ema_rgb, 1.0);
  textureStore(out_tex, vec2<u32>(gid.xy), out_px);
  textureStore(out_next_prev, vec2<u32>(gid.xy), out_px);
}