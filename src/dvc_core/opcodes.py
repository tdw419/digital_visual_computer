from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Instruction:
    op: str
    arg: Optional[str] = None


OPCODES = {
    "NOP",
    "HALT",
    "PUSHI",
    "POP",
    "ADD",
    "SUB",
    "MUL",
    "DIV",
    "PRINT",
    # Graphics Primitives
    "RECT_FILL",
    "TEXT_RENDER",
}


def validate_instruction(instr: Instruction) -> None:
    if instr.op not in OPCODES:
        raise ValueError(f"Unknown opcode: {instr.op}")

    ops_with_arg = {"PUSHI", "TEXT_RENDER"}
    if instr.op in ops_with_arg and instr.arg is None:
        raise ValueError(f"{instr.op} requires an argument")
    if instr.op not in ops_with_arg and instr.arg is not None:
        raise ValueError(f"{instr.op} must not have an argument")

