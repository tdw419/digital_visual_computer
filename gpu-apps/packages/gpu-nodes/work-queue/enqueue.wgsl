// Ring-buffer enqueue over a 1-row r32float storage texture.
// Each thread attempts to enqueue one value by CAS on tail.
// enqueue_src: read values from row 0 at x = thread index (use .r)
// queue_tex dims: width = capacity, height >= row+1
// enqueued_mask: row 0 gets 1 if this lane enqueued, else 0

struct QueuePtrs {
  head: atomic<u32>,
  tail: atomic<u32>,
  capacity: u32,
  row: u32
};

@group(0) @binding(2) var enqueue_src: texture_2d<f32>;
@group(0) @binding(3) var queue_tex: texture_storage_2d<r32float, read_write>;
@group(0) @binding(4) var<storage, read_write> ptrs: QueuePtrs;
@group(0) @binding(5) var enq_mask: texture_storage_2d<r32float, write>;

fn wrap(i: u32, cap: u32) -> u32 { return select(i, i - cap, i >= cap); }

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let lane = gid.x;
  let cap = ptrs.capacity;
  if (cap == 0u) { return; }

  var claimed = false;
  var my_idx = 0u;
  loop {
    let old_tail = atomicLoad(&ptrs.tail);
    let head = atomicLoad(&ptrs.head);
    let next = wrap(old_tail + 1u, cap);
    // Full if next catches head
    if (next == head) { break; }
    let cas = atomicCompareExchangeWeak(&ptrs.tail, old_tail, next);
    if (cas.exchanged) {
      claimed = true;
      my_idx = old_tail;
      break;
    }
    continuing { }
  }

  var wrote = 0.0;
  if (claimed) {
    let val = textureLoad(enqueue_src, vec2<i32>(i32(lane), 0), 0).r;
    textureStore(queue_tex, vec2<u32>(my_idx, ptrs.row), vec4<f32>(val, 0.0, 0.0, 1.0));
    wrote = 1.0;
  }
  textureStore(enq_mask, vec2<u32>(lane, 0u), vec4<f32>(wrote, 0.0, 0.0, 1.0));
}