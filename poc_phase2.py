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
    (0, 255, 0): '+',
    (255, 0, 255): 'DRAW_PIXEL',
}

def parse_image_to_tokens(filename: str) -> List[str]:
    if not Image: raise ImportError("Pillow library is required.")
    with Image.open(filename) as img:
        rgb_img = img.convert('RGB')
        width, height = img.size
        tokens = []
        for y in range(height):
            for x in range(width):
                tokens.append(INSTRUCTION_MAP.get(rgb_img.getpixel((x, y)), 'NOP'))
    return tokens

class TextRenderer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = [['.' for _ in range(width)] for _ in range(height)]

    def draw_pixel(self, x: int, y: int, color: str = 'X'):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = color

    def display(self):
        for row in self.grid:
            print(" ".join(row))

class RPN_VM_Spatial:
    def __init__(self, renderer: TextRenderer):
        self.stack: List[int] = []
        self.renderer = renderer

    def run(self, tokens: List[str]):
        number_buffer = ""
        for token in tokens:
            if token == 'START':
                self.stack = []
                number_buffer = ""
            elif token.isdigit():
                number_buffer += token
            elif token == 'SEP':
                if number_buffer: self.stack.append(int(number_buffer)); number_buffer = ""
            elif token == 'DRAW_PIXEL':
                if number_buffer: self.stack.append(int(number_buffer)); number_buffer = ""
                if len(self.stack) < 2: raise ValueError("Stack underflow for DRAW_PIXEL")
                y = self.stack.pop()
                x = self.stack.pop()
                self.renderer.draw_pixel(x, y)
            elif token == 'END':
                break

def main():
    program_file = "program_phase2.png"
    print(f"Attempting to run program from '{program_file}'...")

    if not os.path.exists(program_file):
        print(f"Error: Program file '{program_file}' not found.")
        return

    try:
        tokens = parse_image_to_tokens(program_file)
        print(f"Successfully parsed {len(tokens)} tokens.")

        renderer = TextRenderer(10, 10)
        vm = RPN_VM_Spatial(renderer)
        vm.run(tokens)

        print("\n--- Rendered Output ---")
        renderer.display()
        print("-----------------------")

    except (ValueError, ZeroDivisionError, ImportError) as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
