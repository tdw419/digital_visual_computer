# color_engine/vector_space.py
import numpy as np

def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x)
    e = np.exp(x)
    return e / np.sum(e)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

class VectorColorSpace:
    """
    Each color is a fixed embedding vector (deterministic, seedable).
    Color ops = vector ops. Default dim=64 for speed.
    """
    def __init__(self, dim: int = 64, seed: int = 1337):
        self.dim = dim
        rnd = np.random.default_rng(seed)
        # Core palette (edit/extend freely)
        self.colors = [
            '🔵','🟦','💠',  # input/data/structured
            '🟣','🟪',       # transform/process
            '🟢','💚','✅',  # success/validated/done
            '🟡','🟠','🔴',  # monitor/warn/critical
            '🚨','🔍','🔧','👨','📊',  # incident/search/fix/human/monitor
            '➡️','🔄','⬆️','🧠','💾'   # flow/loop/escalate/think/store
        ]
        self.emb = {c: self._unit(rnd.normal(size=dim)) for c in self.colors}

    def _unit(self, v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        return v / n if n else v

    def vec(self, color: str) -> np.ndarray:
        if color not in self.emb:
            # auto-extend palette deterministically
            h = abs(hash(color)) % (10**6)
            rnd = np.random.default_rng(h)
            self.emb[color] = self._unit(rnd.normal(size=self.dim))
        return self.emb[color]

    def nearest(self, v: np.ndarray) -> str:
        best_c, best_s = None, -1.0
        for c, e in self.emb.items():
            s = cosine_sim(v, e)
            if s > best_s:
                best_c, best_s = c, s
        return best_c

    def blend(self, c1: str, c2: str, w: float = 0.5) -> str:
        v = self.vec(c1)*w + self.vec(c2)*(1.0 - w)
        return self.nearest(v)
