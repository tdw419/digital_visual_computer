"""
PixelText Library
A library for encoding and decoding data within PNG images according to the
PixelText v1.1 specification.
"""

from .encoder import encode
from .decoder import decode

__all__ = ['encode', 'decode']