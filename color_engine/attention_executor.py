# color_engine/attention_executor.py
from typing import List, Tuple
import numpy as np
from .vector_space import VectorColorSpace, softmax, cosine_sim
from .pattern_encoder import PatternEncoder

class AttentionExecutor:
    """
    Single-layer attention: all cells attend to all cells in parallel.
    Lightweight: Q=K=V=identity in this MVP (pure similarity field).
    """
    def __init__(self, space: VectorColorSpace):
        self.space = space
        self.encoder = PatternEncoder(space)

    def execute(self, grid: List[List[str]]) -> Tuple[List[List[str]], np.ndarray]:
        # flatten -> embeddings
        cells = [(r, c, self.space.vec(color))
                 for r, row in enumerate(grid)
                 for c, color in enumerate(row)]
        if not cells:
            return grid, np.zeros((0, 0))

        V = np.stack([v for _,_,v in cells])          # (N, D)
        # attention scores = cosine(V, V)
        N = V.shape[0]
        S = np.zeros((N, N), dtype=float)
        for i in range(N):
            for j in range(N):
                S[i, j] = cosine_sim(V[i], V[j])

        # normalize row-wise (softmax)
        W = np.apply_along_axis(softmax, 1, S)        # (N, N)
        O = W @ V                                      # (N, D)

        # map outputs back to nearest colors, rebuild grid
        out_colors = [self.space.nearest(O[i]) for i in range(N)]

        if not grid or not grid[0]:
            return [], W

        rows = len(grid)
        cols = len(grid[0])
        out = []
        k = 0
        for r in range(rows):
            row = []
            for c in range(cols):
                if k < len(out_colors):
                    row.append(out_colors[k])
                k += 1
            out.append(row)
        return out, W
