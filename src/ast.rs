#[derive(Debug)]
pub struct Program {
    pub version: f32,
    pub texture: TextureDecl,
    pub kernel: Kernel,
    pub frame: Frame,
}

#[derive(Debug)]
pub struct TextureDecl {
    pub name: String,
    pub format: TextureFormat,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug)]
pub enum TextureFormat { Rgba16f }

#[derive(Debug)]
pub struct Kernel {
    pub name: String,
    // pub param: String, // This is now implicit
    pub stmts: Vec<Stmt>,
    pub ret: Expr,
}

#[derive(Debug)]
pub struct Frame {
    pub call_kernel: String, // e.g., "render"
}

#[derive(Debug)]
pub enum Stmt {
    Let { name: String, expr: Expr },
}

#[derive(Debug, Clone)]
pub enum Expr {
    Float(f32),
    Ident(String),
    Field(Box<Expr>, String),         // a.b
    CastF32(Box<Expr>),               // f32(expr)
    Div(Box<Expr>, Box<Expr>),        // a / b
    Vec4(Box<Expr>, Box<Expr>, Box<Expr>, Box<Expr>),
}