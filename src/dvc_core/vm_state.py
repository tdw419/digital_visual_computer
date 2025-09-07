from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class VMState:
    ip: int = 0
    stack: List[int] = field(default_factory=list)
    outputs: List[int] = field(default_factory=list)
    status: str = "running"  # running|halted|faulted

