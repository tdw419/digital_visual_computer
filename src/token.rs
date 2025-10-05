#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Kw {
    Lang, Texture, Kernel, EachPixel, Frame, Present, Let,
    Ivec2, F32, Vec4, Rgba16f,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    Kw(Kw),
    Ident(String),
    Int(u32),
    Float(f32),

    At, Colon, Semi, Comma,
    LParen, RParen, LBrace, RBrace,
    Dot, Eq, Slash, X, // X is the 'x' between dims (e.g., 512x512)
}