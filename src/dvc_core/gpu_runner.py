from __future__ import annotations

import wgpu
import numpy as np

# WGSL implementation of the DVC VM, based on Pixel ISA v0.1
VM_SHADER_CODE = """
struct VMState {
    pc: u32,
    status: u32, // 0: running, 1: halted
    regs: array<u32, 16>,
};

@group(0) @binding(0) var<storage, read_write> state: VMState;
@group(0) @binding(1) var code: texture_2d<f32>;
@group(0) @binding(2) var<storage, read_write> memory: array<u32>;

const STEP_LIMIT = 10000u;

// --- WASM Interpreter Helpers ---
var<private> wasm_pc: u32;
var<private> wasm_sp: u32;
var<private> wasm_locals_ptr: u32;

fn read_u8(addr: u32) -> u32 {
    let word_addr = addr / 4u;
    let byte_offset = addr % 4u;
    let word = memory[word_addr];
    return (word >> (byte_offset * 8u)) & 0xFFu;
}

fn wasm_push(val: u32) {
    memory[wasm_sp] = val;
    wasm_sp = wasm_sp + 1u;
}

fn wasm_pop() -> u32 {
    wasm_sp = wasm_sp - 1u;
    return memory[wasm_sp];
}

fn interpret_wasm() {
    // This is a very basic interpreter loop, executing up to 100 WASM opcodes.
    for (var i: u32 = 0u; i < 100u; i = i + 1u) {
        let opcode = read_u8(wasm_pc);
        wasm_pc = wasm_pc + 1u;

        switch (opcode) {
            case 0x20u: { // local.get
                // This is a simplified implementation that doesn't handle LEB128 decoding.
                let local_index = read_u8(wasm_pc);
                wasm_pc = wasm_pc + 1u;
                wasm_push(memory[wasm_locals_ptr + local_index]);
            }
            case 0x6au: { // i32.add
                let b = wasm_pop();
                let a = wasm_pop();
                wasm_push(a + b);
            }
            case 0x0bu: { // end
                return; // End of function
            }
            default: {
                // Unknown opcode, exit interpreter
                return;
            }
        }
    }
}
// --- End WASM Interpreter ---


@compute @workgroup_size(1)
fn main() {
    for (var i: u32 = 0u; i < STEP_LIMIT; i = i + 1u) {
        if (state.status != 0u) {
            break;
        }

        let pc_coord = vec2<i32>(i32(state.pc), 0);
        let instr_pixel = textureLoad(code, pc_coord, 0);

        let opcode = u32(instr_pixel.r * 255.0);
        let arg0 = u32(instr_pixel.g * 255.0);
        let arg1 = u32(instr_pixel.b * 255.0);
        let arg2 = u32(instr_pixel.a * 255.0);

        var next_pc = state.pc + 1u;

        switch (opcode) {
            case 0x00u: { // NOP
                // Do nothing
            }
            case 0x01u: { // HALT
                state.status = 1u;
            }
            case 0x10u: { // LOAD_CONST
                state.regs[arg0] = arg1;
            }
            case 0x11u: { // MOV
                state.regs[arg0] = state.regs[arg1];
            }
            case 0x20u: { // ADD
                state.regs[arg0] = state.regs[arg1] + state.regs[arg2];
            }
            case 0x21u: { // SUB
                state.regs[arg0] = state.regs[arg1] - state.regs[arg2];
            }
            case 0x30u: { // LOAD_MEM
                let addr = state.regs[arg1];
                state.regs[arg0] = memory[addr];
            }
            case 0x31u: { // STORE_MEM
                let addr = state.regs[arg1];
                let val = state.regs[arg0];
                memory[addr] = val;
            }
            case 0x40u: { // JUMP
                next_pc = state.regs[arg0];
            }
            case 0x41u: { // JUMP_IF_ZERO
                if (state.regs[arg1] == 0u) {
                    next_pc = state.regs[arg0];
                }
            }
            case 0x50u: { // SYSCALL
                if (arg0 == 0u) { // Enter WASM interpreter
                    // Use registers to pass wasm_pc, wasm_sp, and wasm_locals_ptr
                    wasm_pc = state.regs[arg1];
                    wasm_sp = state.regs[arg2];
                    wasm_locals_ptr = state.regs[13]; // Convention: r13 holds locals pointer

                    interpret_wasm();

                    // Write back the updated pointers
                    state.regs[arg1] = wasm_pc;
                    state.regs[arg2] = wasm_sp;
                }
            }
            default: {
                // Unknown opcode, halt
                state.status = 1u;
            }
        }
        state.pc = next_pc;
    }
}
"""

from .program import Program
from typing import Optional

def run_gpu(program: Program, wasm_bytecode: Optional[bytes] = None):
    """
    Runs the DVC VM on the GPU using the Pixel ISA.
    """
    # 1. Initialize WGPU
    adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
    device = adapter.request_device_sync()
    shader = device.create_shader_module(code=VM_SHADER_CODE)

    # 2. Assemble program into pixel format (RGBA8)
    num_instructions = len(program.instructions)
    instruction_data = np.zeros((num_instructions, 4), dtype=np.uint8)

    op_map = {
        "NOP": 0x00, "HALT": 0x01, "LOAD_CONST": 0x10, "MOV": 0x11,
        "ADD": 0x20, "SUB": 0x21, "LOAD_MEM": 0x30, "STORE_MEM": 0x31,
        "JUMP": 0x40, "JUMP_IF_ZERO": 0x41, "SYSCALL": 0x50
    }

    for i, instr in enumerate(program.instructions):
        instruction_data[i, 0] = op_map.get(instr.op, 0)
        parts = [int(p) for p in instr.arg.split(',')] if instr.arg else []
        instruction_data[i, 1] = parts[0] if len(parts) > 0 else 0
        instruction_data[i, 2] = parts[1] if len(parts) > 1 else 0
        instruction_data[i, 3] = parts[2] if len(parts) > 2 else 0

    # 3. Create GPU resources
    texture_size = (num_instructions, 1, 1)
    texture = device.create_texture(
        size=texture_size,
        usage=wgpu.TextureUsage.TEXTURE_BINDING | wgpu.TextureUsage.COPY_DST,
        dimension=wgpu.TextureDimension.d2,
        format=wgpu.TextureFormat.rgba8unorm,
    )
    device.queue.write_texture(
        {"texture": texture, "mip_level": 0, "origin": (0, 0, 0)},
        instruction_data,
        {"bytes_per_row": num_instructions * 4, "rows_per_image": 1},
        texture_size,
    )

    vm_state_data = np.zeros(18, dtype=np.uint32)
    vm_state_buffer = device.create_buffer_with_data(data=vm_state_data, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)

    memory_buffer = device.create_buffer(size=65536, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC | wgpu.BufferUsage.COPY_DST)

    if wasm_bytecode:
        # Pad bytecode to be a multiple of 4 bytes for alignment
        padding_size = (4 - len(wasm_bytecode) % 4) % 4
        padded_bytecode = wasm_bytecode + (b'\x00' * padding_size)
        device.queue.write_buffer(memory_buffer, 0, padded_bytecode)

    # 4. Setup pipeline
    binding_layouts = [
        {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}},
        {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE, "texture": {"sample_type": wgpu.TextureSampleType.float}},
        {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}},
    ]
    bind_group_layout = device.create_bind_group_layout(entries=binding_layouts)
    pipeline_layout = device.create_pipeline_layout(bind_group_layouts=[bind_group_layout])

    bind_group = device.create_bind_group(
        layout=bind_group_layout,
        entries=[
            {"binding": 0, "resource": {"buffer": vm_state_buffer, "offset": 0, "size": vm_state_buffer.size}},
            {"binding": 1, "resource": texture.create_view()},
            {"binding": 2, "resource": {"buffer": memory_buffer, "offset": 0, "size": memory_buffer.size}},
        ],
    )

    compute_pipeline = device.create_compute_pipeline(
        layout=pipeline_layout,
        compute={"module": shader, "entry_point": "main"},
    )

    # 5. Run shader
    command_encoder = device.create_command_encoder()
    compute_pass = command_encoder.begin_compute_pass()
    compute_pass.set_pipeline(compute_pipeline)
    compute_pass.set_bind_group(0, bind_group)
    compute_pass.dispatch_workgroups(1)
    compute_pass.end()
    device.queue.submit([command_encoder.finish()])

    # 6. Read back results
    final_state_data = device.queue.read_buffer(vm_state_buffer).tobytes()
    final_state = np.frombuffer(final_state_data, dtype=np.uint32)

    final_memory_data = device.queue.read_buffer(memory_buffer).tobytes()
    final_memory = np.frombuffer(final_memory_data, dtype=np.uint32)

    return {
        "final_state": {
            "pc": final_state[0],
            "status": final_state[1],
            "regs": final_state[2:].tolist(),
        },
        "final_memory": final_memory.tolist(),
    }