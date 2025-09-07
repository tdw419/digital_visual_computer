"""
Color language specific exception types.
"""


class ColorLangError(Exception):
    """Base exception for color language errors."""
    pass


class PaletteError(ColorLangError):
    """Error in palette loading, validation, or color matching."""
    pass


class ImageError(ColorLangError):
    """Error in PNG image loading or processing."""
    pass


class CompilerError(ColorLangError):
    """Error in color compilation pipeline."""
    pass