use crate::token::{Kw, Token};

fn kw_of(s: &str) -> Option<Kw> {
    Some(match s {
        "lang" => Kw::Lang,
        "texture" => Kw::Texture,
        "kernel" => Kw::Kernel,
        "each_pixel" => Kw::EachPixel,
        "frame" => Kw::Frame,
        "present" => Kw::Present,
        "let" => Kw::Let,
        "ivec2" => Kw::Ivec2,
        "f32" => Kw::F32,
        "vec4" => Kw::Vec4,
        "rgba16f" => Kw::Rgba16f,
        _ => return None,
    })
}

pub fn tokenize(src: &str) -> Vec<Token> {
    let mut it = src.chars().peekable();
    let mut out = Vec::new();

    while let Some(&c) = it.peek() {
        // whitespace
        if c.is_whitespace() { it.next(); continue; }

        // line comment //
        if c == '/' {
            it.next();
            if let Some('/') = it.peek().copied() {
                it.next();
                while let Some(ch) = it.peek().copied() {
                    it.next();
                    if ch == '\n' { break; }
                }
                continue;
            } else {
                out.push(Token::Slash);
                continue;
            }
        }

        // numbers
        if c.is_ascii_digit() || (c == '.' && it.clone().nth(1).map_or(false, |c| c.is_ascii_digit())) {
            let mut s = String::new();
            let mut has_dot = c == '.';
            s.push(it.next().unwrap());
            while let Some(&n) = it.peek() {
                if n.is_ascii_digit() {
                    s.push(n); it.next();
                } else if n == '.' && !has_dot {
                    has_dot = true; s.push(n); it.next();
                } else { break; }
            }
            if has_dot {
                out.push(Token::Float(s.parse::<f32>().expect("float parse")));
            } else {
                out.push(Token::Int(s.parse::<u32>().expect("int parse")));
            }
            continue;
        }

        // identifiers / keywords
        if c.is_ascii_alphabetic() || c == '_' {
            let mut s = String::new();
            s.push(it.next().unwrap());
            while let Some(&n) = it.peek() {
                // If we have an "x", don't consume subsequent digits.
                if s == "x" && n.is_ascii_digit() {
                    break;
                }
                if n.is_ascii_alphanumeric() || n == '_' {
                    s.push(n); it.next();
                } else { break; }
            }
            if let Some(kw) = kw_of(&s) {
                out.push(Token::Kw(kw));
            } else if s == "x" {
                out.push(Token::X);
            } else {
                out.push(Token::Ident(s));
            }
            continue;
        }

        // punctuation
        match it.next().unwrap() {
            '@' => out.push(Token::At),
            ':' => out.push(Token::Colon),
            ';' => out.push(Token::Semi),
            ',' => out.push(Token::Comma),
            '(' => out.push(Token::LParen),
            ')' => out.push(Token::RParen),
            '{' => out.push(Token::LBrace),
            '}' => out.push(Token::RBrace),
            '.' => out.push(Token::Dot),
            '=' => out.push(Token::Eq),
            other => panic!("Unexpected char: {}", other),
        }
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::token::Kw as K;

    #[test]
    fn tokenizes_minimal_header() {
        let t = tokenize("lang 0.1\ntexture fb: rgba16f @ 512x512;");
        assert_eq!(t[0], Token::Kw(K::Lang));
        assert!(matches!(t[1], Token::Float(f) if (f - 0.1).abs() < 1e-6));
        assert_eq!(t[2], Token::Kw(K::Texture));
        assert_eq!(t[3], Token::Ident("fb".into()));
        assert_eq!(t[4], Token::Colon);
        assert_eq!(t[5], Token::Kw(K::Rgba16f));
        assert_eq!(t[6], Token::At);
        assert_eq!(t[7], Token::Int(512));
        assert_eq!(t[8], Token::X);
        assert_eq!(t[9], Token::Int(512));
        assert_eq!(t[10], Token::Semi);
    }
}