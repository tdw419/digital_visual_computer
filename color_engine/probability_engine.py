# color_engine/probability_engine.py
from typing import List
import numpy as np
from .vector_space import VectorColorSpace

class ProbabilityEngine:
    """
    Gradients as smooth decisions; blend multiple actions by weights.
    """
    def __init__(self, space: VectorColorSpace):
        self.space = space

    def gradient(self, start: str, end: str, t: float) -> str:
        t = max(0.0, min(1.0, t))
        v = self.space.vec(start)*(1-t) + self.space.vec(end)*t
        return self.space.nearest(v)

    def blend_weighted(self, colors: List[str], weights: List[float]) -> str:
        w = np.array(weights, dtype=float)
        w = w / (w.sum() if w.sum() else 1.0)
        v = np.zeros(self.space.dim)
        for c, p in zip(colors, w):
            v += self.space.vec(c) * p
        return self.space.nearest(v)
