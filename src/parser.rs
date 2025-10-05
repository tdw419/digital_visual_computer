use crate::ast::*;
use crate::token::{Kw as K, Token};

pub struct Parser {
    toks: Vec<Token>,
    i: usize,
}

impl Parser {
    pub fn new(toks: Vec<Token>) -> Self { Self { toks, i: 0 } }
    fn peek(&self) -> Option<&Token> { self.toks.get(self.i) }
    fn bump(&mut self) -> Token { self.i += 1; self.toks[self.i-1].clone() }

    fn expect(&mut self, want: Token) {
        let got = self.bump();
        assert_eq!(got, want, "expected {:?}, got {:?}", want, got);
    }

    fn expect_kw(&mut self, k: K) {
        let got = self.bump();
        assert!(matches!(got, Token::Kw(k2) if k2 == k), "expected {:?}, got {:?}", k, got);
    }

    fn expect_ident(&mut self) -> String {
        if let Token::Ident(s) = self.bump() { s } else { panic!("ident expected") }
    }

    fn expect_int(&mut self) -> u32 {
        if let Token::Int(v) = self.bump() { v } else { panic!("int expected") }
    }

    fn expect_float(&mut self) -> f32 {
        if let Token::Float(v) = self.bump() { v } else { panic!("float expected") }
    }

    fn parse_version(&mut self) -> f32 {
        self.expect_kw(K::Lang);
        match self.bump() {
            Token::Float(v) => v,
            Token::Int(v) => v as f32,
            t => panic!("version number expected, got {:?}", t),
        }
    }

    fn parse_texture(&mut self) -> TextureDecl {
        self.expect_kw(K::Texture);
        let name = self.expect_ident();
        self.expect(Token::Colon);
        self.expect_kw(K::Rgba16f);
        self.expect(Token::At);
        let w = self.expect_int();
        self.expect(Token::X);
        let h = self.expect_int();
        self.expect(Token::Semi);
        TextureDecl { name, format: TextureFormat::Rgba16f, width: w, height: h }
    }

    fn parse_kernel(&mut self) -> Kernel {
        self.expect_kw(K::Kernel);
        let name = self.expect_ident();
        self.expect_kw(K::EachPixel);
        self.expect(Token::LBrace);

        // body: zero or more let-statements, then final expr without ';'
        let mut stmts = Vec::new();
        loop {
            match self.peek() {
                Some(Token::Kw(K::Let)) => {
                    self.bump(); // let
                    let nm = self.expect_ident();
                    self.expect(Token::Eq);
                    let ex = self.parse_expr();
                    self.expect(Token::Semi);
                    stmts.push(Stmt::Let { name: nm, expr: ex });
                }
                _ => break,
            }
        }
        let ret = self.parse_expr();
        self.expect(Token::RBrace);
        Kernel { name, stmts, ret }
    }

    fn parse_frame(&mut self) -> Frame {
        self.expect_kw(K::Frame);
        self.expect(Token::LBrace);
        self.expect_kw(K::Present);
        let kn = self.expect_ident();
        self.expect(Token::Semi);
        self.expect(Token::RBrace);
        Frame { call_kernel: kn }
    }

    fn parse_expr(&mut self) -> Expr { self.parse_div() }

    fn parse_div(&mut self) -> Expr {
        let mut left = self.parse_primary();
        while matches!(self.peek(), Some(Token::Slash)) {
            self.bump(); // '/'
            let right = self.parse_primary();
            left = Expr::Div(Box::new(left), Box::new(right));
        }
        left
    }

    fn parse_primary(&mut self) -> Expr {
        match self.bump() {
            Token::Float(f) => Expr::Float(f),
            Token::Int(i)   => Expr::Float(i as f32),
            Token::Ident(s) => {
                // possible field chain: ident(.ident)*
                let mut e = Expr::Ident(s);
                while matches!(self.peek(), Some(Token::Dot)) {
                    self.bump(); // '.'
                    let fld = match self.bump() {
                        Token::Ident(s) => s,
                        Token::X => "x".to_string(),
                        other => panic!("field ident expected, got {:?}", other),
                    };
                    e = Expr::Field(Box::new(e), fld);
                }
                e
            }
            Token::Kw(K::F32) => {
                self.expect(Token::LParen);
                let inner = self.parse_expr();
                self.expect(Token::RParen);
                Expr::CastF32(Box::new(inner))
            }
            Token::Kw(K::Vec4) => {
                self.expect(Token::LParen);
                let a = self.parse_expr(); self.expect(Token::Comma);
                let b = self.parse_expr(); self.expect(Token::Comma);
                let c = self.parse_expr(); self.expect(Token::Comma);
                let d = self.parse_expr();
                self.expect(Token::RParen);
                Expr::Vec4(Box::new(a), Box::new(b), Box::new(c), Box::new(d))
            }
            t => panic!("expr start unexpected: {:?}", t),
        }
    }
}

pub fn parse_program(toks: Vec<Token>) -> Program {
    let mut p = Parser::new(toks);
    let version = p.parse_version();
    let texture = p.parse_texture();
    let kernel  = p.parse_kernel();
    let frame   = p.parse_frame();
    Program { version, texture, kernel, frame }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{lexer::tokenize, ast::Expr};

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
    fn parses_minimal() {
        let prog = parse_program(tokenize(SRC));
        assert!((prog.version - 0.1).abs() < 1e-6);
        assert_eq!(prog.texture.name, "fb");
        assert_eq!(prog.texture.width, 512);
        assert_eq!(prog.texture.height, 512);
        assert_eq!(prog.kernel.name, "render");
        assert_eq!(prog.frame.call_kernel, "render");

        // Check that "pixel.x" is parsed correctly
        let first_let_expr = &prog.kernel.stmts[0];
        if let crate::ast::Stmt::Let { expr, .. } = first_let_expr {
             if let Expr::Div(left, _) = expr {
                if let Expr::CastF32(inner) = &**left {
                    if let Expr::Field(base, field) = &**inner {
                        if let Expr::Ident(name) = &**base {
                            assert_eq!(name, "pixel");
                            assert_eq!(field, "x");
                        } else { panic!("Expected ident") }
                    } else { panic!("Expected field access") }
                } else { panic!("Expected f32 cast") }
             } else { panic!("Expected division") }
        } else { panic!("Expected let statement") }
    }
}