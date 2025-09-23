import wgpu
import struct
import asyncio

# --- Simplified Core Components for MVP ---

EDITOR_ISA = {
    'INS_CHAR': 1,
    'BKSP': 2,
}

def create_char_buffer(device: wgpu.GPUDevice, initial_text: str, max_len: int) -> wgpu.GPUBuffer:
    initial_data = bytearray(initial_text.encode('utf-32-le'))
    padded_data = initial_data.ljust(max_len * 4, b'\0')
    return device.create_buffer_with_data(
        data=padded_data,
        usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC | wgpu.BufferUsage.COPY_DST
    )

async def read_buffer(device: wgpu.GPUDevice, buffer: wgpu.GPUBuffer) -> bytes:
    """Helper function to read data back from a GPU buffer."""
    size = buffer.size
    output_buffer = device.create_buffer(size=size, usage=wgpu.BufferUsage.COPY_DST | wgpu.BufferUsage.MAP_READ)
    command_encoder = device.create_command_encoder()
    command_encoder.copy_buffer_to_buffer(buffer, 0, output_buffer, 0, size)
    device.queue.submit([command_encoder.finish()])
    await output_buffer.map_async(wgpu.MapMode.READ)
    data = output_buffer.read_mapped_range()
    return bytes(data)

async def main():
    """The verifiable host runner."""
    print("--- Starting Verifiable Host Runner for Editor MVP ---")

    try:
        adapter = await wgpu.request_adapter(power_preference="high-performance")
        device = await adapter.request_device()
    except Exception as e:
        print(f"Failed to initialize WebGPU: {e}")
        print("This script requires a WebGPU-compatible GPU and drivers.")
        return

    # 1. Load Shader
    try:
        with open("../shaders/mvp_edit_kernel.wgsl", "r") as f:
            shader_code = f.read()
        shader_module = device.create_shader_module(code=shader_code)
    except FileNotFoundError:
        print("Error: `shaders/mvp_edit_kernel.wgsl` not found.")
        print("Please ensure you are running this script from the repository root.")
        return

    # 2. Setup Pipeline
    binding_layouts = [
        {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}},
        {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.uniform}},
    ]
    bind_group_layout = device.create_bind_group_layout(entries=binding_layouts)
    pipeline_layout = device.create_pipeline_layout(bind_group_layouts=[bind_group_layout])
    compute_pipeline = device.create_compute_pipeline(
        layout=pipeline_layout,
        compute={"module": shader_module, "entry_point": "main"}
    )

    # --- 3. Verification Test ---
    buffer_max_len = 16 # 16 characters

    # Test Case 1: Insert 'o' into "hell"
    print("\n--- Test Case 1: INS_CHAR 'o' ---")
    char_buffer = create_char_buffer(device, "hell", buffer_max_len)

    # Uniforms: opcode=1 (INS_CHAR), char_code=ord('o'), cursor_pos=4
    uniform_data = struct.pack("<3I", EDITOR_ISA['INS_CHAR'], ord('o'), 4)
    uniform_buffer = device.create_buffer_with_data(data=uniform_data, usage=wgpu.BufferUsage.UNIFORM)

    bind_group = device.create_bind_group(
        layout=bind_group_layout,
        entries=[
            {"binding": 0, "resource": {"buffer": char_buffer, "offset": 0, "size": char_buffer.size}},
            {"binding": 1, "resource": {"buffer": uniform_buffer, "offset": 0, "size": uniform_buffer.size}},
        ]
    )

    command_encoder = device.create_command_encoder()
    compute_pass = command_encoder.begin_compute_pass()
    compute_pass.set_pipeline(compute_pipeline)
    compute_pass.set_bind_group(0, bind_group, [], 0, 999999)
    compute_pass.dispatch_workgroups(1)
    compute_pass.end()
    device.queue.submit([command_encoder.finish()])

    # Read back and verify
    result_bytes = await read_buffer(device, char_buffer)
    result_str = result_bytes.decode('utf-32-le').rstrip('\x00')

    print(f"Expected: 'hello', Got: '{result_str}'")
    assert result_str == "hello"
    print("✅ Verification PASSED")

    # Test Case 2: Backspace from "hello"
    print("\n--- Test Case 2: BKSP ---")
    # char_buffer already contains "hello"

    # Uniforms: opcode=2 (BKSP), char_code=0, cursor_pos=5
    uniform_data = struct.pack("<3I", EDITOR_ISA['BKSP'], 0, 5)
    device.queue.write_buffer(uniform_buffer, 0, uniform_data)

    command_encoder = device.create_command_encoder()
    compute_pass = command_encoder.begin_compute_pass()
    compute_pass.set_pipeline(compute_pipeline)
    compute_pass.set_bind_group(0, bind_group, [], 0, 999999)
    compute_pass.dispatch_workgroups(1)
    compute_pass.end()
    device.queue.submit([command_encoder.finish()])

    result_bytes = await read_buffer(device, char_buffer)
    result_str = result_bytes.decode('utf-32-le').rstrip('\x00')

    print(f"Expected: 'hell', Got: '{result_str}'")
    assert result_str == "hell"
    print("✅ Verification PASSED")

    print("\n--- All MVP tests passed! ---")


if __name__ == "__main__":
    # wgpu uses an async event loop, so we run our main function in it.
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred during execution: {e}")
