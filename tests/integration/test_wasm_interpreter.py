import pytest
import numpy as np
from dvc_core.program import Program
from dvc_core.opcodes import Instruction
from dvc_core.gpu_runner import run_gpu

# This is the WASM bytecode for a simple function:
# (module
#   (func (export "add") (param i32 i32) (result i32)
#     local.get 0
#     local.get 1
#     i32.add
#   )
# )
# Compiled using an online tool.
WASM_ADD_BYTECODE = bytes([
    0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x07, 0x01, 0x60,
    0x02, 0x7f, 0x7f, 0x01, 0x7f, 0x03, 0x02, 0x01, 0x00, 0x07, 0x07, 0x01,
    0x03, 0x61, 0x64, 0x64, 0x00, 0x00, 0x0a, 0x09, 0x01, 0x07, 0x00, 0x20,
    0x00, 0x20, 0x01, 0x6a, 0x0b
])

def test_wasm_add_function_on_gpu():
    """
    Tests the execution of a simple WASM 'add' function on the GPU.
    This test verifies the implementation of the WASM interpreter for
    local.get and i32.add opcodes.
    """
    # Memory layout for this test:
    # 0-43: WASM bytecode (padded)
    # ...
    # 64-65: Local variables (function arguments: 5 and 7)
    # 66 onwards: Value stack

    WASM_PC_START = 35  # Start of the function body in the bytecode
    LOCALS_PTR = 64
    STACK_PTR_START = 66

    program_instructions = [
        # Set up arguments for the WASM function
        Instruction(op="LOAD_CONST", arg=f"0,{5}"),          # r0 = 5
        Instruction(op="LOAD_CONST", arg=f"1,{LOCALS_PTR}"), # r1 = locals_ptr
        Instruction(op="STORE_MEM", arg="0,1"),            # memory[locals_ptr] = 5

        Instruction(op="LOAD_CONST", arg=f"0,{7}"),                # r0 = 7
        Instruction(op="LOAD_CONST", arg=f"1,{LOCALS_PTR + 1}"), # r1 = locals_ptr + 1
        Instruction(op="STORE_MEM", arg="0,1"),                  # memory[locals_ptr + 1] = 7

        # Set up registers for the WASM interpreter call
        Instruction(op="LOAD_CONST", arg=f"1,{WASM_PC_START}"), # r1 = wasm_pc
        Instruction(op="LOAD_CONST", arg=f"2,{STACK_PTR_START}"), # r2 = wasm_sp
        Instruction(op="LOAD_CONST", arg=f"13,{LOCALS_PTR}"),    # r13 = wasm_locals_ptr

        # Call the WASM interpreter
        Instruction(op="SYSCALL", arg="0,1,2"), # syscall 0, passing registers 1 and 2

        Instruction(op="HALT"),
    ]
    program = Program(instructions=program_instructions)

    result = run_gpu(program, wasm_bytecode=WASM_ADD_BYTECODE)

    final_memory = result["final_memory"]

    # The result of the add operation (5 + 7 = 12) should be on the stack.
    # The stack starts at index 66. After the operation, the result is at the new top of the stack.
    # The interpreter pushes two values, then pops them and pushes one result.
    # So the final result is at the initial stack pointer address.
    assert final_memory[STACK_PTR_START] == 12, "The result of the WASM add function should be on the stack"