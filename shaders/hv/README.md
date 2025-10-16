# HV (GPU Hypervisor) — M0 → M1 WGSL

## Bindings (group(0))
B0: uniform IOHeader
B1: storage(read_write) guest_ram        (u32[], >= 64 MiB / 16M u32)
B2: storage(read)       disk_iso         (u32[], ISO as words, immutable)
B3: storage(read_write) hv_state         (fits VCPU + misc)
B4: storage(read_write) event_ring       (optional; unused here)
T0: texture_storage_2d<rgba8unorm, write> console target (cols x rows)

## Pipeline order per frame
1) hv_tick (workgroups: 1,1,1)
2) hv_console_blt (workgroups: ceil(cols/8), ceil(rows/8), 1)

> You can also call hv_console_blt only every N frames.

## IOHeader packing (u32 fields, 16B multiples)
steps_per_tick: e.g., 10000
ram_words:      guest_ram length in u32
iso_words:      disk_iso length in u32
cols, rows:     e.g., 80, 25
flags:          0

## Acceptance checks

M0:
- On first frame(s), the seeded MBR runs: console shows at least four white cells ("GPU!").
- hv_state.stage == STAGE_REALMODE (1)
- No watchdog (bounded loop)

M1:
- Write minimal test snippet into RAM at 0x7C00 that:
  * MOV CX, (LBA low)
  * MOV DX, (LBA high)
  * MOV AX, 0x0201     ; AH=02 (read), AL=1 sector
  * MOV ES, seg ; MOV BX, offs   ; destination
  * INT 13h
  * … inspect dst bytes via teletype

Notes:
- INT 13h path here is **HLE, LBA-only**, using CX:DX for starting LBA.
- For “real” ISOLINUX later, add CHS decode or implement AH=0x42 (DAP).

## Tripwire
- If the guest executes `0F 22 C0` (MOV CR0,EAX), hv_state.stage := 2 (PM_TRIPWIRE) and vCPU halts.

## Safety
- All loops are bounded by `steps_per_tick`.
- All buffer accesses are guarded by arrayLength/word-based checks.
- `@workgroup_size(1)` for hv_tick ⇒ safe single writer of guest_ram.