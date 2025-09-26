import pytest
from dvc_core.program import Program
from dvc_core.opcodes import Instruction
from dvc_core.gpu_runner import run_gpu

def test_pixel_isa_simple_arithmetic():
    """
    Tests basic arithmetic on the Pixel ISA GPU VM.
    """
    program_instructions = [
        Instruction(op="LOAD_CONST", arg="0,2"),   # regs[0] = 2
        Instruction(op="LOAD_CONST", arg="1,3"),   # regs[1] = 3
        Instruction(op="ADD", arg="2,0,1"),        # regs[2] = regs[0] + regs[1]
        Instruction(op="HALT"),
    ]
    program = Program(instructions=program_instructions)

    result = run_gpu(program)

    # Check final state
    final_state = result["final_state"]
    assert final_state["status"] == 1, "VM should be halted"
    assert final_state["pc"] == 4, "PC should be at the instruction after HALT"
    assert final_state["regs"][0] == 2, "Register 0 should hold the value 2"
    assert final_state["regs"][1] == 3, "Register 1 should hold the value 3"
    assert final_state["regs"][2] == 5, "Register 2 should hold the sum 5"

def test_pixel_isa_memory_operations():
    """
    Tests LOAD_MEM and STORE_MEM operations on the Pixel ISA GPU VM.
    """
    program_instructions = [
        Instruction(op="LOAD_CONST", arg="0,42"),      # regs[0] = 42 (value to store)
        Instruction(op="LOAD_CONST", arg="1,100"),     # regs[1] = 100 (memory address)
        Instruction(op="STORE_MEM", arg="0,1"),       # memory[100] = 42
        Instruction(op="LOAD_MEM", arg="2,1"),        # regs[2] = memory[100]
        Instruction(op="HALT"),
    ]
    program = Program(instructions=program_instructions)

    result = run_gpu(program)

    # Check final state
    final_state = result["final_state"]
    final_memory = result["final_memory"]

    assert final_state["status"] == 1, "VM should be halted"
    assert final_state["regs"][0] == 42
    assert final_state["regs"][1] == 100
    assert final_state["regs"][2] == 42
    assert final_memory[100] == 42