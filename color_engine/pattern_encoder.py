# color_engine/pattern_encoder.py
import math
from typing import List
import numpy as np
from .vector_space import VectorColorSpace

class PatternEncoder:
    """
    Encode a 2D grid of colors to a single vector (mean of (color+pos) embeddings).
    Positional enc: simple sin/cos over row/col.
    """
    def __init__(self, space: VectorColorSpace):
        self.space = space
        self.dim = space.dim

    def _pos(self, r: int, c: int) -> np.ndarray:
        v = np.zeros(self.dim, dtype=float)
        for i in range(0, self.dim, 4):
            # interleave row/col sin/cos
            v[i+0] = math.sin(r / (10000 ** (i / max(1,self.dim))))
            v[i+1] = math.cos(r / (10000 ** (i / max(1,self.dim))))
            v[i+2] = math.sin(c / (10000 ** (i / max(1,self.dim))))
            v[i+3] = math.cos(c / (10000 ** (i / max(1,self.dim))))
        return v

    def encode_grid(self, grid: List[List[str]]) -> np.ndarray:
        acc = []
        for r, row in enumerate(grid):
            for c, color in enumerate(row):
                acc.append(self.space.vec(color) + self._pos(r, c))
        return np.mean(acc, axis=0) if acc else np.zeros(self.dim, dtype=float)
