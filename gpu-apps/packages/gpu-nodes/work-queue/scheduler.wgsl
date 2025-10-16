// Dequeue one job per lane and bump a per-job atomic counter.
// Job ID is derived from the dequeued value (rounded, clamped).
// processed_ids_out row 0 gets the processed job id (or -1 if none).

struct QueuePtrs {
  head: atomic<u32>,
  tail: atomic<u32>,
  capacity: u32,
  row: u32
};

struct SchedulerParams {
  num_counters: u32,
  _pad0: vec3<u32>
};

struct JobCounters {
  counts: array<atomic<u32>>
};

@group(0) @binding(0) var<uniform> P: SchedulerParams;
@group(0) @binding(3) var queue_tex: texture_storage_2d<r32float, read_write>;
@group(0) @binding(4) var<storage, read_write> ptrs: QueuePtrs;
@group(0) @binding(5) var processed_ids_out: texture_storage_2d<r32float, write>;
@group(0) @binding(6) var<storage, read_write> JC: JobCounters;

fn wrap(i: u32, cap: u32) -> u32 { return select(i, i - cap, i >= cap); }

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let lane = gid.x;
  let cap = ptrs.capacity;
  if (cap == 0u || P.num_counters == 0u) { return; }

  // Fast-empty
  if (atomicLoad(&ptrs.head) == atomicLoad(&ptrs.tail)) {
    textureStore(processed_ids_out, vec2<u32>(lane, 0u), vec4<f32>(-1.0,0.0,0.0,1.0));
    return;
  }

  // Claim one slot by incrementing head
  var claimed = false;
  var my_idx = 0u;
  loop {
    let old_head = atomicLoad(&ptrs.head);
    let tail = atomicLoad(&ptrs.tail);
    if (old_head == tail) { break; }
    let next = wrap(old_head + 1u, cap);
    let cas = atomicCompareExchangeWeak(&ptrs.head, old_head, next);
    if (cas.exchanged) {
      claimed = true;
      my_idx = old_head;
      break;
    }
    continuing { }
  }

  if (!claimed) {
    textureStore(processed_ids_out, vec2<u32>(lane, 0u), vec4<f32>(-1.0,0.0,0.0,1.0));
    return;
  }

  // Read job value, map to counter index, bump
  let px = vec2<i32>(i32(my_idx), i32(ptrs.row));
  let val = textureLoad(queue_tex, px).r;
  let jid = clamp(i32(round(val)), 0, i32(P.num_counters) - 1);
  atomicAdd(&JC.counts[u32(jid)], 1u);
  textureStore(processed_ids_out, vec2<u32>(lane, 0u), vec4<f32>(f32(jid),0.0,0.0,1.0));

  // Optional: clear consumed slot
  textureStore(queue_tex, vec2<u32>(my_idx, ptrs.row), vec4<f32>(0.0,0.0,0.0,1.0));
}