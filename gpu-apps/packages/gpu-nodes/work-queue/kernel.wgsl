// Ring-buffer queue over a 1-row r32float storage texture.
// Each thread attempts to dequeue one element by CAS on head.
// queue_tex dims: width = capacity, height >= row+1
// dequeue_out: first row receives popped values at x = thread index

struct QueuePtrs {
  head: atomic<u32>,
  tail: atomic<u32>,
  capacity: u32,
  row: u32
};

@group(0) @binding(3) var queue_tex: texture_storage_2d<r32float, read_write>;
@group(0) @binding(4) var<storage, read_write> ptrs: QueuePtrs;
@group(0) @binding(5) var dq_out: texture_storage_2d<r32float, write>;

fn wrap(i: u32, cap: u32) -> u32 { return select(i, i - cap, i >= cap); }

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let lane = gid.x;
  let cap = ptrs.capacity;
  if (cap == 0u) { return; }

  // Fast-empty check
  if (atomicLoad(&ptrs.head) == atomicLoad(&ptrs.tail)) { return; }

  // Try to claim one slot by incrementing head
  var claimed = false;
  var my_idx = 0u;
  loop {
    let old_head = atomicLoad(&ptrs.head);
    let tail = atomicLoad(&ptrs.tail);
    if (old_head == tail) { break; } // empty now
    let next = wrap(old_head + 1u, cap);
    let cas = atomicCompareExchangeWeak(&ptrs.head, old_head, next);
    if (cas.exchanged) {
      claimed = true;
      my_idx = old_head;
      break;
    }
    continuing { }
  }

  if (!claimed) { return; }

  // Read value and write to output row 0 at x = lane
  let row = i32(ptrs.row);
  let px = vec2<i32>(i32(my_idx), row);
  let val = textureLoad(queue_tex, px).r;
  textureStore(dq_out, vec2<u32>(lane, 0u), vec4<f32>(val, 0.0, 0.0, 1.0));

  // Optional: clear the consumed slot (not required for correctness)
  textureStore(queue_tex, vec2<u32>(my_idx, ptrs.row), vec4<f32>(0.0,0.0,0.0,1.0));
}