import os
from typing import List, Tuple, Any

try:
    from PIL import Image
except ImportError:
    print("Pillow library not found. Please install it with 'pip install Pillow'")
    Image = None

INSTRUCTION_MAP = {
    (0, 0, 0): 'START',
    (255, 255, 255): 'END',
    (128, 128, 128): 'SEP',
    (10, 0, 0): '1', (20, 0, 0): '2', (30, 0, 0): '3', (40, 0, 0): '4', (50, 0, 0): '5',
    (60, 0, 0): '6', (70, 0, 0): '7', (80, 0, 0): '8', (90, 0, 0): '9',
    (0, 255, 0): '+', (0, 200, 0): '-', (0, 0, 255): '*', (0, 0, 200): '/',
    (255, 215, 0): '=',
}

def parse_image_to_tokens(filename: str) -> List[str]:
    if not Image: raise ImportError("Pillow library is required.")

    with Image.open(filename) as img:
        rgb_img = img.convert('RGB')
        width, height = img.size
        tokens = []
        for y in range(height):
            for x in range(width):
                rgb = rgb_img.getpixel((x, y))
                instruction = INSTRUCTION_MAP.get(rgb)
                if instruction is None:
                    raise ValueError(f"Unknown instruction for RGB {rgb} at ({x},{y})")
                tokens.append(instruction)
    return tokens

class RPN_VM:
    def __init__(self):
        self.stack: List[int] = []

    def run(self, tokens: List[str]) -> List[int]:
        self.stack = []
        output = []
        number_buffer = ""

        if not tokens or tokens[0] != 'START':
            raise ValueError("Program must start with a START token.")

        for token in tokens[1:]:
            if token.isdigit():
                number_buffer += token
            elif token == 'SEP':
                if number_buffer:
                    self.stack.append(int(number_buffer))
                    number_buffer = ""
            elif token in ['+', '-', '*', '/']:
                if number_buffer:
                    self.stack.append(int(number_buffer))
                    number_buffer = ""
                if len(self.stack) < 2:
                    raise ValueError(f"Stack underflow for operator '{token}'")
                b = self.stack.pop()
                a = self.stack.pop()
                if token == '+': self.stack.append(a + b)
                elif token == '-': self.stack.append(a - b)
                elif token == '*': self.stack.append(a * b)
                elif token == '/':
                    if b == 0: raise ZeroDivisionError("Division by zero")
                    self.stack.append(a // b)
            elif token == '=':
                if self.stack:
                    output.append(self.stack[-1])
            elif token == 'END':
                break

        return output

def main():
    program_file = "program_phase1.png"
    print(f"Attempting to run program from '{program_file}'...")

    if not os.path.exists(program_file):
        print(f"Error: Program file '{program_file}' not found.")
        return

    try:
        tokens = parse_image_to_tokens(program_file)
        print(f"Successfully parsed {len(tokens)} tokens: {tokens}")

        vm = RPN_VM()
        results = vm.run(tokens)

        if results:
            print(f"RESULT: {results[0]}")
        else:
            print("Execution produced no output.")

    except (ValueError, ZeroDivisionError, ImportError) as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
