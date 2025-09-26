from __future__ import annotations

from dvc_core.vm import execute
from dvc_core.program import Program
from dvc_core.opcodes import Instruction
from dvc_core.vm_state import FRAMEBUFFER_WIDTH, FRAMEBUFFER_HEIGHT


def test_color_opcodes():
    # Program to draw a red 'X' on the framebuffer
    instruction_dicts = []
    for i in range(FRAMEBUFFER_WIDTH):
        # Draw top-left to bottom-right diagonal
        instruction_dicts.extend([
            {"op": "PUSHI", "arg": str(i)},
            {"op": "PUSHI", "arg": str(i)},
            {"op": "RED_OP"},
        ])
        # Draw top-right to bottom-left diagonal
        instruction_dicts.extend([
            {"op": "PUSHI", "arg": str(i)},
            {"op": "PUSHI", "arg": str(FRAMEBUFFER_WIDTH - 1 - i)},
            {"op": "RED_OP"},
        ])
    instruction_dicts.append({"op": "HALT"})

    instructions = [
        Instruction(op=instr["op"], arg=instr.get("arg"))
        for instr in instruction_dicts
    ]
    program = Program(instructions=instructions)

    trace = execute(program)

    assert trace["meta"]["halted"]
    assert not trace["meta"]["faulted"]

    framebuffer = trace["meta"]["final_framebuffer"]

    # Verify the 'X' pattern
    for r in range(FRAMEBUFFER_HEIGHT):
        for c in range(FRAMEBUFFER_WIDTH):
            expected_color = 0
            if r == c or r == (FRAMEBUFFER_WIDTH - 1 - c):
                expected_color = 1  # Red

            actual_color = framebuffer[r][c]
            assert actual_color == expected_color, f"Pixel ({r},{c}) was {actual_color} but expected {expected_color}"