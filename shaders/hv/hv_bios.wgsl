// --- INT 10h teletype (AH=0x0E) writes ASCII to console ring ---
fn bios_int10(ax:u32){
  let ah = hi8(ax);
  if (ah != 0x0Eu) { return; }
  let ch = ax & 0xFFu;

  let cols = io_header.cols;
  let rows = io_header.rows;
  let cap = cols * rows;

  let pos = hv_state.console_head % cap;
  st8(hv_state.console_base + pos, ch);
  hv_state.console_head = pos + 1u;
}

// --- INT 13h read sectors (LBA-only HLE) ---
// Contract: we'll interpret CHS params as a *virtual* LBA for now:
// - AL: sector count (we honor only 1..n but bounded)
// - ES:BX: destination buffer
// - CH/DH/CL: ignored; we fetch lba from DX:CX if you want later.
// For immediate progress, add a tiny helper opcode path in your seeded code
// to place the desired LBA in DX:CX (low in CX, high in DX), or hardcode LBAs.
fn bios_int13(v:u32, s:ptr<function, VCPU>){
  // AH already known == 0x02 (READ)
  // sector count in AL
  let count = lo16((*s).ax) & 0xFFu;
  var esbx = ( (*s).es << 4u ) + lo16((*s).bx);
  // read starting LBA from CX:DX (low in CX, high in DX), purely our HLE
  let lba = (lo16((*s).dx) << 16u) | lo16((*s).cx);

  var n:u32 = count;
  var cur_lba:u32 = lba;
  var dst:u32 = esbx;

  // bounded copy
  for (var i:u32=0u; i<n; i++){
    read_sector_lba(cur_lba, dst);
    cur_lba += 1u;
    dst += 512u;
  }
  // set CF=0 on success: flags low bit 0 => leave as is (we don’t model CF yet)
}