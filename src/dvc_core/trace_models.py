from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class TraceMeta:
    version: str
    step_limit: int
    halted: bool
    faulted: bool
    outputs: List[str]
    final_root: str
    started_at: str
    finished_at: str


@dataclass
class TraceStep:
    index: int
    ip: int
    op: str
    arg: Optional[str] = None
    stack_before: List[str] = field(default_factory=list)
    stack_after: List[str] = field(default_factory=list)
    output: Optional[str] = None
    note: Optional[str] = None
    fault: Optional[str] = None
    step_hash: str = ""


def step_to_ordered_dict(step: TraceStep) -> Dict[str, Any]:
    # Preserve key order for readability; hashing uses canonical JSON (sorted keys) elsewhere.
    d: Dict[str, Any] = {
        "index": step.index,
        "ip": step.ip,
        "op": step.op,
    }
    if step.arg is not None:
        d["arg"] = step.arg
    d["stack_before"] = step.stack_before
    d["stack_after"] = step.stack_after
    if step.output is not None:
        d["output"] = step.output
    if step.note is not None:
        d["note"] = step.note
    if step.fault is not None:
        d["fault"] = step.fault
    # step_hash is appended after hashing
    return d

