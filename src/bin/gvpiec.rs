use std::{fs, env};
use gvpie::{tokenize, parse_program, emit_wgsl};

fn main() {
    let mut args = env::args().skip(1);
    let path = args.next().expect("usage: gvpiec <file.gvp> [--check]");
    let check = args.next().map(|a| a == "--check").unwrap_or(false);

    let src = fs::read_to_string(&path).expect("read file");
    let prog = parse_program(tokenize(&src));
    let wgsl = emit_wgsl(&prog);
    println!("{wgsl}");

    #[cfg(feature = "validate")]
    if check {
        naga::front::wgsl::parse_str(&wgsl).expect("WGSL validation failed");
        eprintln!("WGSL OK ✅");
    }
}