from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .opcodes import Instruction, validate_instruction


@dataclass
class Program:
    instructions: List[Instruction]

    @staticmethod
    def from_json_array(arr: list[dict]) -> "Program":
        instrs: List[Instruction] = []
        for i, obj in enumerate(arr):
            if not isinstance(obj, dict) or "op" not in obj:
                raise ValueError(f"Invalid instruction at index {i}")
            op = str(obj["op"])  # enforce string
            arg = obj.get("arg")
            if arg is not None:
                arg = str(arg)  # represent integers as decimal strings
            instr = Instruction(op=op, arg=arg)
            validate_instruction(instr)
            instrs.append(instr)
        return Program(instructions=instrs)

