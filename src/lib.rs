pub mod token;
pub mod lexer;
pub mod ast;
pub mod parser;
pub mod codegen;

pub use lexer::tokenize;
pub use parser::parse_program;
pub use codegen::emit_wgsl;