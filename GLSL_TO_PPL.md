# GLSL → PPL Mapping

This document outlines the conversion mapping from common GLSL functions to their equivalent idioms in the Pixel Programming Language (PPL). This serves as a guide for the `glsl2ppl` converter.

| GLSL                | PPL kernel idiom                                       |
| ------------------- | ------------------------------------------------------ |
| `texture(s, uv)`    | `sample(t, uv)` or `t(px)` when in pixel space         |
| `dFdx(v), dFdy(v)`  | `nbr(px,+1,0).v - nbr(px,-1,0).v`, etc.                |
| `mix(a,b,t)`        | `lerp(a,b,t)`                                          |
| `clamp(x,a,b)`      | `clamp(x,a,b)`                                         |
| `dot(a,b)`          | `dot(a,b)`                                             |
| `normalize(v)`      | `normalize(v)`                                         |
| `step(e,x)`         | `step(e,x)`                                            |
| `smoothstep(a,b,x)` | `smoothstep(a,b,x)`                                    |
| `mat3 * vec3`       | `mul(m,v)`                                             |
| `for (i=0;i<N;i++)` | Prefer map/reduce or explicit `for` with `@time` guard |
| `discard`           | Write to mask / alpha=0 in `Layer`                     |
| `gl_FragColor`      | `px.rgba = …`                                          |
| sRGB↔Linear         | `to_linear(px)`, `to_srgb(px)`                         |
| Premultiply         | `premul(px)`, `unpremul(px)`                           |
| Kernel blur         | `convolve_{exact,approx}(tile, kernel)`                |
| Edge detect         | Neighborhood diffs (`gx/gy`) as shown below            |
| Gamma fix           | `gamma(px, 2.2)`                                       |
| Tone-map            | `tonemap(px, operator=Reinhard)`                       |
| Color mat           | `color_matrix(px, m3x3, offset)`                       |

## Example Fragment Shader → PPL

### GLSL
```glsl
// GLSL
vec4 main(vec2 uv){
  vec3 c = texture(u_tex, uv).rgb;
  float e = abs(dFdx(c.g)) + abs(dFdy(c.g));
  return vec4(min(1.0, c.r + 2.0*e), c.g, c.b, 1.0);
}
```

### PPL
```ppl
kernel edge_boost(t: TileRGBA8) -> TileRGBA8 @time(50µs) {
  for px in t.pixels():
    let gx = abs(nbr(px,+1,0).g - nbr(px,-1,0).g)
    let gy = abs(nbr(px,0,+1).g - nbr(px,0,-1).g)
    let e  = gx + gy
    px.r = min(255, px.r + (e << 1))
  return t
}
```