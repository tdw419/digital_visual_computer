from __future__ import annotations

import wgpu
import numpy as np

# WGSL implementation of the DVC VM
VM_SHADER_CODE = """
struct VMState {
    ip: u32,
    sp: u32,
    status: u32, // 0: running, 1: halted, 2: faulted
};

struct Instruction {
    op: u32,
    arg: u32,
};

// VM state and memory buffers
@group(0) @binding(0) var<storage, read_write> vm_state: VMState;
@group(0) @binding(1) var<storage, read> instructions: array<Instruction>;
@group(0) @binding(2) var<storage, read_write> stack: array<u32>;
@group(0) @binding(3) var<storage, read_write> outputs: array<u32>;
@group(0) @binding(4) var<storage, read_write> framebuffer: array<u32>;

// Constants for opcodes
const NOP: u32 = 0u;
const HALT: u32 = 1u;
const PUSHI: u32 = 2u;
const POP: u32 = 3u;
const ADD: u32 = 4u;
const SUB: u32 = 5u;
const MUL: u32 = 6u;
const DIV: u32 = 7u;
const PRINT: u32 = 8u;
const RED_OP: u32 = 9u;
const GREEN_OP: u32 = 10u;
const BLUE_OP: u32 = 11u;
const WHITE_OP: u32 = 12u;

// Constants for framebuffer
const FRAMEBUFFER_WIDTH: u32 = 16u;

fn push(val: u32) {
    stack[vm_state.sp] = val;
    vm_state.sp = vm_state.sp + 1u;
}

fn pop() -> u32 {
    if (vm_state.sp == 0u) {
        vm_state.status = 2u; // Fault
        return 0u;
    }
    vm_state.sp = vm_state.sp - 1u;
    return stack[vm_state.sp];
}

@compute @workgroup_size(1)
fn main() {
    let instruction_count = arrayLength(&instructions);

    for (var i: u32 = 0u; i < 10000u; i = i + 1u) { // Step limit
        if (vm_state.status != 0u || vm_state.ip >= instruction_count) {
            break;
        }

        let instr = instructions[vm_state.ip];

        switch (instr.op) {
            case NOP: {
                // Do nothing
            }
            case HALT: {
                vm_state.status = 1u;
            }
            case PUSHI: {
                push(instr.arg);
            }
            case POP: {
                _ = pop();
            }
            case ADD: {
                let b = pop(); let a = pop();
                push(a + b);
            }
            case SUB: {
                let b = pop(); let a = pop();
                push(a - b);
            }
            case MUL: {
                let b = pop(); let a = pop();
                push(a * b);
            }
            case DIV: {
                let b = pop(); let a = pop();
                if (b == 0u) {
                    vm_state.status = 2u; // Fault
                } else {
                    push(a / b);
                }
            }
            case PRINT: {
                let val = pop();
                // outputs buffer is not fixed size, can't append.
                // For now, we just write to the first element.
                outputs[0] = val;
            }
            case RED_OP, GREEN_OP, BLUE_OP, WHITE_OP: {
                let y = pop();
                let x = pop();
                let color_val = instr.op - RED_OP + 1u;
                framebuffer[y * FRAMEBUFFER_WIDTH + x] = color_val;
            }
            default: {
                vm_state.status = 2u; // Fault on unknown opcode
            }
        }

        vm_state.ip = vm_state.ip + 1u;
    }
}
"""

from .program import Program
from .vm_state import FRAMEBUFFER_WIDTH, FRAMEBUFFER_HEIGHT
from lib.gpu_assembler import assemble_for_gpu

def run_gpu(program: Program):
    """
    Runs the DVC VM on the GPU using a WGSL compute shader.
    """
    # 1. Initialize WGPU
    adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
    device = adapter.request_device_sync()

    shader = device.create_shader_module(code=VM_SHADER_CODE)

    # 2. Prepare data and create buffers
    # VM State (ip, sp, status)
    vm_state_data = np.array([0, 0, 0], dtype=np.uint32)
    vm_state_buffer = device.create_buffer_with_data(data=vm_state_data, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC | wgpu.BufferUsage.COPY_DST)

    # Instructions
    instruction_data = assemble_for_gpu(program)
    instruction_buffer = device.create_buffer_with_data(data=instruction_data, usage=wgpu.BufferUsage.STORAGE)

    # Stack, Outputs, Framebuffer
    stack_buffer = device.create_buffer(size=1024 * 4, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC) # 1024 u32s
    output_buffer = device.create_buffer(size=256 * 4, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC) # 256 u32s
    framebuffer_size = FRAMEBUFFER_WIDTH * FRAMEBUFFER_HEIGHT * 4
    framebuffer_gpu = device.create_buffer(size=framebuffer_size, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)

    # 3. Setup pipeline
    binding_layouts = [
        {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}},
        {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
        {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}},
        {"binding": 3, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}},
        {"binding": 4, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}},
    ]
    bind_group_layout = device.create_bind_group_layout(entries=binding_layouts)
    pipeline_layout = device.create_pipeline_layout(bind_group_layouts=[bind_group_layout])

    bind_group = device.create_bind_group(
        layout=bind_group_layout,
        entries=[
            {"binding": 0, "resource": {"buffer": vm_state_buffer, "offset": 0, "size": vm_state_buffer.size}},
            {"binding": 1, "resource": {"buffer": instruction_buffer, "offset": 0, "size": instruction_buffer.size}},
            {"binding": 2, "resource": {"buffer": stack_buffer, "offset": 0, "size": stack_buffer.size}},
            {"binding": 3, "resource": {"buffer": output_buffer, "offset": 0, "size": output_buffer.size}},
            {"binding": 4, "resource": {"buffer": framebuffer_gpu, "offset": 0, "size": framebuffer_gpu.size}},
        ],
    )

    compute_pipeline = device.create_compute_pipeline(
        layout=pipeline_layout,
        compute={"module": shader, "entry_point": "main"},
    )

    # 4. Run shader
    command_encoder = device.create_command_encoder()
    compute_pass = command_encoder.begin_compute_pass()
    compute_pass.set_pipeline(compute_pipeline)
    compute_pass.set_bind_group(0, bind_group)
    compute_pass.dispatch_workgroups(1)
    compute_pass.end()
    device.queue.submit([command_encoder.finish()])

    # 5. Read back results
    result_data = device.queue.read_buffer(framebuffer_gpu).tobytes()
    framebuffer_flat = np.frombuffer(result_data, dtype=np.uint32)

    # Reshape the flat array back into the 2D framebuffer
    framebuffer = framebuffer_flat.reshape((FRAMEBUFFER_HEIGHT, FRAMEBUFFER_WIDTH)).tolist()

    return {
        "final_framebuffer": framebuffer,
        "status": "halted" # Placeholder status
    }