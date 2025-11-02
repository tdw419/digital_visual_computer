# color_engine/pattern_memory.py
from dataclasses import dataclass, field
from typing import List, Dict, Any
import numpy as np
from .vector_space import VectorColorSpace, cosine_sim
from .pattern_encoder import PatternEncoder

@dataclass
class PatternMemory:
    space: VectorColorSpace
    encoder: PatternEncoder
    records: List[Dict[str, Any]] = field(default_factory=list)

    def store(self, grid: List[List[str]], outcome: Dict[str, Any]):
        emb = self.encoder.encode_grid(grid).tolist()
        self.records.append({"grid": grid, "emb": emb, "outcome": outcome})

    def similar(self, grid: List[List[str]], k: int = 5) -> List[Dict[str, Any]]:
        if not self.records: return []
        q = self.encoder.encode_grid(grid)
        scored = []
        for rec in self.records:
            s = cosine_sim(q, np.array(rec["emb"]))
            scored.append((s, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored[:k]]
