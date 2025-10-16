// --- bindings (match your plan) ---
// B0: uniform IOHeader
// B1: storage(read_write) guest_ram
// B2: storage(read) disk_iso  (ISO as u32 buffer)
// B3: storage(read_write) hv_state
// B4: storage(read_write) event_ring
// T0: texture_storage_2d<rgba8unorm, write> (console)

struct IOHeader {
  steps_per_tick : u32;   // how many ops this dispatch can do
  ram_words      : u32;   // guest_ram length in u32
  iso_words      : u32;   // disk_iso length in u32
  cols           : u32;   // console cols (e.g., 80)
  rows           : u32;   // console rows (e.g., 25)
  flags          : u32;   // reserved
  _pad0          : u32;
};

@group(0) @binding(0) var<uniform> io_header : IOHeader;
@group(0) @binding(1) var<storage, read_write> guest_ram : array<u32>;
@group(0) @binding(2) var<storage, read>       disk_iso  : array<u32>;

// console texture target
@group(0) @binding(5) var console_tex : texture_storage_2d<rgba8unorm, write>;

// ---- hv_state ----

struct VCPU {
  // 16-bit real mode regs kept in low 16 of u32
  ax:u32; bx:u32; cx:u32; dx:u32;
  si:u32; di:u32; bp:u32; sp:u32;
  ip:u32; flags:u32;
  cs:u32; ds:u32; es:u32; ss:u32;

  state:u32;  // 1=RUNNING, 0=HALTED
  _pad:u32;
};

const STAGE_INIT              : u32 = 0u;
const STAGE_REALMODE          : u32 = 1u;
const STAGE_PM_TRIPWIRE       : u32 = 2u;

struct HVState {
  stage:u32;
  console_head:u32;   // index in char grid (wrap cols*rows)
  disk_heads:u32;     // fake geometry for CHS→LBA (if needed later)
  disk_spt:u32;       // sectors per track (but we do LBA-only for now)

  // text grid base (guest RAM offset in bytes)
  console_base:u32;   // where chars are stored (1 byte each)
  _pad0:u32;

  vcpu: array<VCPU, 1>;
};

@group(0) @binding(3) var<storage, read_write> hv_state : HVState;
@group(0) @binding(4) var<storage, read_write> event_ring : array<u32>; // not used yet

// convenience
fn lo16(x:u32)->u32 { return x & 0xFFFFu; }
fn hi8(x:u32)->u32 { return (x >> 8u) & 0xFFu; }