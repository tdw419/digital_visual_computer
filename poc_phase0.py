import os
from typing import Tuple, Optional

try:
    from PIL import Image
except ImportError:
    print("Pillow library not found. Please install it with 'pip install Pillow'")
    Image = None

INSTRUCTION_MAP = {
    (255, 0, 0): "PRINT_HELLO",
    (0, 255, 0): "PRINT_GOODBYE",
}

class CompilerError(Exception):
    def __init__(self, message, position, rgb_value):
        super().__init__(f"At {position}: {message} (RGB: {rgb_value})")
        self.position = position
        self.rgb_value = rgb_value

def parse_pixel(rgb: Tuple[int, int, int], position: Tuple[int, int] = (0, 0)) -> str:
    instruction = INSTRUCTION_MAP.get(rgb)
    if instruction is None:
        raise CompilerError("Unknown instruction", position, rgb)
    return instruction

def execute_instruction(instruction: str):
    if instruction == "PRINT_HELLO":
        print("Hello from Pixel Programming!")
    elif instruction == "PRINT_GOODBYE":
        print("Goodbye from Pixel Programming!")
    else:
        print(f"FAILURE: Unknown instruction '{instruction}'")

def run_program_from_png(filename: str):
    print(f"Attempting to run program from '{filename}'...")
    if not Image:
        return

    if not os.path.exists(filename):
        print(f"Error: Program file '{filename}' not found.")
        print("Please create a 1x1 PNG with a red (255,0,0) or green (0,255,0) pixel.")
        return

    try:
        with Image.open(filename) as img:
            if img.size != (1, 1):
                print(f"Error: Expected a 1x1 pixel image, but got {img.size}.")
                return

            rgb_img = img.convert('RGB')
            rgb_tuple = rgb_img.getpixel((0, 0))

            print(f"Loaded pixel with RGB: {rgb_tuple}")

            instruction = parse_pixel(rgb_tuple)
            execute_instruction(instruction)

    except CompilerError as e:
        print(f"Compilation Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    program_file = "program.png"
    run_program_from_png(program_file)
