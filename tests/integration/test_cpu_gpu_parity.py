from __future__ import annotations

import pytest
from dvc_core.vm import execute
from dvc_core.gpu_runner import run_gpu
from dvc_core.program import Program
from dvc_core.opcodes import Instruction
from dvc_core.vm_state import FRAMEBUFFER_WIDTH, FRAMEBUFFER_HEIGHT

def create_test_program() -> Program:
    """
    Creates a program that draws a complex pattern to test all color opcodes.
    """
    instruction_dicts = []
    # Draw a checkerboard pattern
    for r in range(FRAMEBUFFER_HEIGHT):
        for c in range(FRAMEBUFFER_WIDTH):
            if (r + c) % 2 == 0:
                instruction_dicts.extend([
                    {"op": "PUSHI", "arg": str(c)},
                    {"op": "PUSHI", "arg": str(r)},
                    {"op": "WHITE_OP"},
                ])
            else:
                instruction_dicts.extend([
                    {"op": "PUSHI", "arg": str(c)},
                    {"op": "PUSHI", "arg": str(r)},
                    {"op": "BLUE_OP"},
                ])
    instruction_dicts.append({"op": "HALT"})

    instructions = [
        Instruction(op=instr["op"], arg=instr.get("arg"))
        for instr in instruction_dicts
    ]
    return Program(instructions=instructions)

def test_cpu_gpu_framebuffer_parity():
    """
    Tests that the CPU and GPU VMs produce identical framebuffers for the same program.
    """
    program = create_test_program()

    # Run on CPU
    cpu_trace = execute(program)
    cpu_framebuffer = cpu_trace["meta"]["final_framebuffer"]

    # Run on GPU
    gpu_result = run_gpu(program)
    gpu_framebuffer = gpu_result["final_framebuffer"]

    # Compare framebuffers
    assert cpu_framebuffer == gpu_framebuffer, "CPU and GPU framebuffers do not match!"