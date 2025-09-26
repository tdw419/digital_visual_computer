from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


FRAMEBUFFER_WIDTH = 16
FRAMEBUFFER_HEIGHT = 16


@dataclass
class VMState:
    ip: int = 0
    stack: List[int] = field(default_factory=list)
    outputs: List[int] = field(default_factory=list)
    status: str = "running"  # running|halted|faulted
    framebuffer: List[List[int]] = field(
        default_factory=lambda: [
            [0] * FRAMEBUFFER_WIDTH for _ in range(FRAMEBUFFER_HEIGHT)
        ]
    )

