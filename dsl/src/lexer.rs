#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    Keyword(&'static str),
    Identifier(String),
    Number(f64),
}

const KEYWORDS: &[&str] = &[
    "lang",
    "texture",
    "kernel",
    "each_pixel",
    "frame",
    "present",
    "let",
];

fn classify_token_piece(piece: &str) -> Token {
    if let Ok(n) = piece.parse::<f64>() {
        return Token::Number(n);
    }

    if KEYWORDS.contains(&piece) {
        return Token::Keyword(match piece {
            "lang" => "lang",
            "texture" => "texture",
            "kernel" => "kernel",
            "each_pixel" => "each_pixel",
            "frame" => "frame",
            "present" => "present",
            "let" => "let",
            _ => unreachable!(),
        });
    }

    Token::Identifier(piece.to_string())
}

pub fn tokenize(src: &str) -> Vec<Token> {
    let mut tokens: Vec<Token> = Vec::new();
    for piece in src.split_whitespace() {
        tokens.push(classify_token_piece(piece));
    }
    tokens
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tokenizes_minimal() {
        let tokens = tokenize("lang 0.1\ntexture fb: rgba16f @ 512x512;");
        assert_eq!(tokens[0], Token::Keyword("lang"));
        assert_eq!(tokens[1], Token::Number(0.1));
        // Spot check a few more
        assert_eq!(tokens[2], Token::Keyword("texture"));
        assert_eq!(tokens.last().unwrap(), &Token::Identifier("512x512;".to_string()));
    }
}
