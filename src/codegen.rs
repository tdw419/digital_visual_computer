use crate::ast::*;

fn emit_expr(e: &Expr) -> String {
    match e {
        Expr::Float(f) => {
            // always emit with decimal to be f32
            if f.fract() == 0.0 { format!("{}.{:}", *f as i32, 0) } else { format!("{}", f) }
        }
        Expr::Ident(s) => s.clone(),
        Expr::Field(base, fld) => format!("{}.{}", emit_expr(base), fld),
        Expr::CastF32(inner) => format!("f32({})", emit_expr(inner)),
        Expr::Div(a, b) => format!("({} / {})", emit_expr(a), emit_expr(b)),
        Expr::Vec4(a,b,c,d) => format!("vec4<f32>({}, {}, {}, {})",
                                       emit_expr(a), emit_expr(b), emit_expr(c), emit_expr(d)),
    }
}

pub fn emit_wgsl(p: &Program) -> String {
    let (w, h) = (p.texture.width, p.texture.height);
    let mut body = String::new();
    for s in &p.kernel.stmts {
        match s {
            Stmt::Let { name, expr } => {
                body.push_str(&format!("  let {}: f32 = {};\n", name, emit_expr(expr)));
            }
        }
    }
    let ret = emit_expr(&p.kernel.ret);

    let storage_format = match p.texture.format {
        TextureFormat::Rgba16f => "rgba16float",
    };

    format!(r#"
const WIDTH:  u32 = {w}u;
const HEIGHT: u32 = {h}u;

@group(0) @binding(0)
var fb: texture_storage_2d<{fmt}, write>;

@compute @workgroup_size(8, 8)
fn {kname}(@builtin(global_invocation_id) gid: vec3<u32>) {{
  if (gid.x >= WIDTH || gid.y >= HEIGHT) {{ return; }}
  let pixel = vec2<i32>(i32(gid.x), i32(gid.y));
{body}  let out: vec4<f32> = {ret};
  textureStore(fb, pixel, out);
}}
"#, w=w, h=h, fmt=storage_format, kname=&p.kernel.name, body=body, ret=ret)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{lexer::tokenize, parser::parse_program};

    const SRC: &str = r#"
lang 0.1
texture fb: rgba16f @ 512x512;

kernel render each_pixel {
  let r = f32(pixel.x) / 512.0;
  let g = f32(pixel.y) / 512.0;
  vec4(r, g, 0.0, 1.0)
}

frame { present render; }
"#;

    #[test]
    fn emits_wgsl() {
        let prog = parse_program(tokenize(SRC));
        let wgsl = emit_wgsl(&prog);
        assert!(wgsl.contains("texture_storage_2d<rgba16float, write>"));
        assert!(wgsl.contains("fn render("));
        assert!(wgsl.contains("let pixel = vec2<i32>(i32(gid.x), i32(gid.y));"));
    }

    #[cfg(feature = "validate")]
    #[test]
    fn validate_with_naga() {
        let prog = crate::parse_program(crate::tokenize(SRC));
        let wgsl = emit_wgsl(&prog);
        let _ = naga::front::wgsl::parse_str(&wgsl).expect("WGSL should parse");
    }
}