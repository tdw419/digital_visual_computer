# color_engine/engine.py
from typing import List, Dict, Any
from .vector_space import VectorColorSpace
from .pattern_encoder import PatternEncoder
from .attention_executor import AttentionExecutor
from .probability_engine import ProbabilityEngine
from .pattern_memory import PatternMemory

class ColorEngine:
    def __init__(self, dim: int = 64, seed: int = 1337):
        self.space = VectorColorSpace(dim, seed)
        self.encoder = PatternEncoder(self.space)
        self.attn = AttentionExecutor(self.space)
        self.prob = ProbabilityEngine(self.space)
        self.mem = PatternMemory(self.space, self.encoder)

    # Think = vectorize → find similar → parallel execute → confidence hint
    def think(self, grid: List[List[str]]) -> Dict[str, Any]:
        out, W = self.attn.execute(grid)
        sims = self.mem.similar(grid, k=5)
        conf = float(W.mean()) if W.size else 0.0
        return {
            "input": grid,
            "output": out,
            "attention_mean": conf,
            "similar_found": len(sims),
            "top_outcome": sims[0]["outcome"] if sims else None
        }

    def learn(self, grid: List[List[str]], success: bool, note: str = ""):
        self.mem.store(grid, {"success": success, "note": note})
