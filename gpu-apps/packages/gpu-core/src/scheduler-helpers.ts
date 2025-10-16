/**
 * 1. Creates and writes the SchedulerParams uniform buffer (@group(0)@binding(0)).
 * The buffer holds the 'num_counters' value, padded to 16 bytes for alignment.
 *
 * @param device The WebGPU device.
 * @param numCounters The total number of atomic job counters required.
 * @returns The initialized GPUBuffer for SchedulerParams.
 */
export function createSchedulerParamsBuffer(device: GPUDevice, numCounters: number): GPUBuffer {
    // struct SchedulerParams { num_counters: u32; _pad0: vec3<u32>; };
    const paramsArray = new Uint32Array([
        numCounters, // num_counters
        0,           // _pad0.x
        0,           // _pad0.y
        0            // _pad0.z
    ]);

    const buffer = device.createBuffer({
        size: paramsArray.byteLength,
        usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });

    device.queue.writeBuffer(buffer, 0, paramsArray);
    return buffer;
}

/**
 * 2. Creates and initializes the JobCounters storage buffer (@group(0)@binding(6)).
 * This buffer holds a runtime-sized array of atomic<u32> counters.
 *
 * @param device The WebGPU device.
 * @param numCounters The total number of atomic job counters required.
 * @returns The initialized (zeroed) GPUBuffer for JobCounters.
 */
export function createJobCountersBuffer(device: GPUDevice, numCounters: number): GPUBuffer {
    // struct JobCounters { counts: array<atomic<u32>>; };
    const sizeInBytes = numCounters * 4; // Each u32 is 4 bytes

    const buffer = device.createBuffer({
        size: sizeInBytes,
        usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST,
    });

    // Initialize counters to zero
    const zeroData = new Uint8Array(sizeInBytes).fill(0);
    device.queue.writeBuffer(buffer, 0, zeroData);

    return buffer;
}

/**
 * Creates the QueuePtrs storage buffer, initializing head, tail, capacity, and row.
 *
 * @param device The WebGPU device.
 * @param capacity The maximum number of items the queue can hold.
 * @param row The texture row used for the queue payload.
 * @returns The initialized GPUBuffer for QueuePtrs.
 */
export function createQueuePtrsBuffer(device: GPUDevice, capacity: number, row: number = 0): GPUBuffer {
    // struct QueuePtrs { head: atomic<u32>; tail: atomic<u32>; capacity: u32; row: u32; };
    const ptrsArray = new Uint32Array([0, 0, capacity, row]); // Initial: head=0, tail=0

    const buffer = device.createBuffer({
        size: ptrsArray.byteLength,
        usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });

    device.queue.writeBuffer(buffer, 0, ptrsArray);
    return buffer;
}