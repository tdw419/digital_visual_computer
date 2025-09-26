from __future__ import annotations

import numpy as np
from dvc_core.program import Program

# Mapping of opcode strings to their integer representation in the shader
OPCODE_MAP = {
    "NOP": 0,
    "HALT": 1,
    "PUSHI": 2,
    "POP": 3,
    "ADD": 4,
    "SUB": 5,
    "MUL": 6,
    "DIV": 7,
    "PRINT": 8,
    "RED_OP": 9,
    "GREEN_OP": 10,
    "BLUE_OP": 11,
    "WHITE_OP": 12,
}

def assemble_for_gpu(program: Program) -> np.ndarray:
    """
    Assembles a Program object into a numpy array suitable for the GPU.
    Each instruction is converted into two 32-bit integers: [opcode, arg].
    """
    instruction_data = np.zeros(len(program.instructions) * 2, dtype=np.uint32)
    for i, instr in enumerate(program.instructions):
        op_code = OPCODE_MAP.get(instr.op)
        if op_code is None:
            raise ValueError(f"Unknown opcode during assembly: {instr.op}")

        arg = int(instr.arg) if instr.arg is not None else 0

        instruction_data[i * 2] = op_code
        instruction_data[i * 2 + 1] = arg

    return instruction_data