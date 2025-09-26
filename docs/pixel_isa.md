# Pixel ISA v0.1

This document specifies the v0.1 instruction set architecture for the Digital Visual Computer's GPU-native VM.

## Instruction Format

Instructions are encoded in a 32-bit format, corresponding to the four 8-bit channels of a single pixel (RGBA8).

- **R (Red Channel):** 8-bit Opcode
- **G (Green Channel):** 8-bit Argument 0 (arg0)
- **B (Blue Channel):** 8-bit Argument 1 (arg1)
- **A (Alpha Channel):** 8-bit Argument 2 (arg2)

## Registers

The VM has a small set of general-purpose registers, which will be defined in the VM state. For now, we will assume at least 16 registers (r0-r15).

## Opcodes

| Opcode (Hex) | Mnemonic      | `arg0`      | `arg1`      | `arg2`      | Description                                       |
|--------------|---------------|-------------|-------------|-------------|---------------------------------------------------|
| `0x00`       | `NOP`         | -           | -           | -           | No operation.                                     |
| `0x01`       | `HALT`        | -           | -           | -           | Halts the VM.                                     |
| `0x10`       | `LOAD_CONST`  | `dst_reg`   | `const_val` | -           | `reg[dst_reg] = const_val`                        |
| `0x11`       | `MOV`         | `dst_reg`   | `src_reg`   | -           | `reg[dst_reg] = reg[src_reg]`                     |
| `0x20`       | `ADD`         | `dst_reg`   | `src_reg1`  | `src_reg2`  | `reg[dst_reg] = reg[src_reg1] + reg[src_reg2]`    |
| `0x21`       | `SUB`         | `dst_reg`   | `src_reg1`  | `src_reg2`  | `reg[dst_reg] = reg[src_reg1] - reg[src_reg2]`    |
| `0x30`       | `LOAD_MEM`    | `dst_reg`   | `addr_reg`  | -           | `reg[dst_reg] = memory[reg[addr_reg]]`            |
| `0x31`       | `STORE_MEM`   | `src_reg`   | `addr_reg`  | -           | `memory[reg[addr_reg]] = reg[src_reg]`            |
| `0x40`       | `JUMP`        | `addr_reg`  | -           | -           | `pc = reg[addr_reg]`                              |
| `0x41`       | `JUMP_IF_ZERO`| `addr_reg`  | `cond_reg`  | -           | `if reg[cond_reg] == 0: pc = reg[addr_reg]`       |
| `0x50`       | `SYSCALL`     | `call_num`  | `arg_reg`   | -           | Triggers a system call (e.g., for I/O).           |

This initial set of opcodes provides a foundation for basic computation, memory access, and control flow, which will be essential for implementing the WASM interpreter. I will expand this ISA as needed.