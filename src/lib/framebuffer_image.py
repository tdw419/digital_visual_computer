from __future__ import annotations

from typing import List
from PIL import Image

# Simple palette for mapping framebuffer values to colors
PALETTE = [
    (0, 0, 0),       # 0: Black
    (255, 0, 0),     # 1: Red
    (0, 255, 0),     # 2: Green
    (0, 0, 255),     # 3: Blue
    (255, 255, 255), # 4: White
]

def save_framebuffer_as_image(framebuffer: List[List[int]], path: str) -> None:
    """
    Saves the framebuffer to a PNG image file.
    """
    height = len(framebuffer)
    if height == 0:
        raise ValueError("Framebuffer has no rows.")
    width = len(framebuffer[0])
    if width == 0:
        raise ValueError("Framebuffer has no columns.")

    img = Image.new("RGB", (width, height))
    pixels = img.load()

    for r in range(height):
        for c in range(width):
            color_index = framebuffer[r][c]
            if 0 <= color_index < len(PALETTE):
                pixels[c, r] = PALETTE[color_index]
            else:
                # Default to black for unknown color indices
                pixels[c, r] = PALETTE[0]

    img.save(path, "PNG")