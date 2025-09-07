"""
Color Language v0.1 - Visual programming with PNG images and color palettes.

This package provides tools for compiling PNG images into DVC JSON IR using
palette-driven color-to-opcode mapping.
"""

from .palette import ColorPalette, PaletteError
from .exceptions import ColorLangError

__version__ = "0.1.0"

__all__ = [
    "ColorPalette", 
    "PaletteError",
    "ColorLangError"
]