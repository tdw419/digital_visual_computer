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
    "RED_OP",
    "GREEN_OP",
    "BLUE_OP",
    "WHITE_OP",
}


def validate_instruction(instr: Instruction) -> None:
    if instr.op not in OPCODES:
        raise ValueError(f"Unknown opcode: {instr.op}")
    if instr.op == "PUSHI" and instr.arg is None:
        raise ValueError("PUSHI requires arg")
    if instr.op != "PUSHI" and instr.arg is not None:
        raise ValueError(f"{instr.op} must not have arg")

