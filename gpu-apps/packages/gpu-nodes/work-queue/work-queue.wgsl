// Payload: queue data in one row (y = queue_row)
@group(0) @binding(0) var queue_tex: texture_storage_2d<r32float, read_write>;

// Atomics for ring buffer
struct QueuePtrs {
  capacity: u32,
  row_y: u32,
  _pad0: u32, _pad1: u32,
  head: atomic<u32>,
  tail: atomic<u32>
};
@group(0) @binding(1) var<storage, read_write> qptr: QueuePtrs;

// ENQUEUE: each invocation writes one value
@compute @workgroup_size(64)
fn queue_enqueue(@builtin(global_invocation_id) gid: vec3<u32>) {
  let idx_in_batch = gid.x;
  // Example value to enqueue
  let val = f32(gid.x);

  let cap = qptr.capacity;
  let y   = qptr.row_y;

  // Claim a slot atomically
  let my_tail_prev = atomicAdd(&qptr.tail, 1u);
  let slot = my_tail_prev % cap;

  // (Optional) simple overflow guard: if queue size >= cap, drop
  let cur_head = atomicLoad(&qptr.head);
  if ((my_tail_prev - cur_head) >= cap) {
    // queue full -> drop or overwrite policy
    return;
  }

  textureStore(queue_tex, vec2<u32>(slot, y), vec4<f32>(val, 0.0, 0.0, 1.0));
}

// DEQUEUE: produce one output row
@group(0) @binding(2) var dequeue_out: texture_storage_2d<r32float, write>;

struct DeqParams { n: u32, out_row_y: u32, _pad: vec2<u32> };
@group(0) @binding(3) var<uniform> deq: DeqParams;

@compute @workgroup_size(64)
fn queue_dequeue(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i = gid.x;
  if (i >= deq.n) { return; }

  let cap = qptr.capacity;
  let y   = qptr.row_y;

  // Atomically advance head once per item
  let my_head_prev = atomicAdd(&qptr.head, 1u);
  // Underflow guard
  let cur_tail = atomicLoad(&qptr.tail);
  if (my_head_prev >= cur_tail) {
    // empty
    return;
  }

  let slot = my_head_prev % cap;
  let v = textureLoad(queue_tex, vec2<i32>(i32(slot), i32(y))).r;
  textureStore(dequeue_out, vec2<u32>(i, deq.out_row_y), vec4<f32>(v,0,0,1));
}