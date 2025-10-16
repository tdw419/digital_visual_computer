#include "hv_common.wgsl"
#include "hv_mem.wgsl"
#include "hv_bios.wgsl"

// --- Minimal Flags helpers ---
const FLAG_C : u32 = 1u << 0u;
const FLAG_Z : u32 = 1u << 6u;
const FLAG_S : u32 = 1u << 7u;
const FLAG_O : u32 = 1u << 11u;

fn get_flag(s:ptr<function, VCPU>, flag:u32) -> bool {
    return ((*s).flags & flag) != 0u;
}

// --- Minimal ModR/M Decoder ---
// This is a simplified decoder for 16-bit addressing modes.
// It returns the effective address and the length of the displacement.
struct ModRMResult {
    addr: u32,
    disp_len: u32,
};
fn decode_modrm(s:ptr<function, VCPU>, pc: u32) -> ModRMResult {
    let modrm_byte = ld8(pc + 1u);
    let mod_ = modrm_byte >> 6u;
    let rm = modrm_byte & 0x07u;

    var addr : u32 = 0u;
    var disp_len : u32 = 0u;

    if (mod_ == 3u) { // Register operand, address is not in memory
        return ModRMResult(0u, 0u);
    }

    switch (rm) {
        case 0u: { addr = lo16((*s).bx) + lo16((*s).si); }
        case 1u: { addr = lo16((*s).bx) + lo16((*s).di); }
        case 2u: { addr = lo16((*s).bp) + lo16((*s).si); }
        case 3u: { addr = lo16((*s).bp) + lo16((*s).di); }
        case 4u: { addr = lo16((*s).si); }
        case 5u: { addr = lo16((*s).di); }
        case 6u: {
            if (mod_ == 0u) { addr = ld16(pc + 2u); disp_len = 2u; }
            else { addr = lo16((*s).bp); }
        }
        case 7u: { addr = lo16((*s).bx); }
        default: {}
    }

    if (mod_ == 1u) { // 8-bit displacement
        addr += ld8(pc + 2u); // Note: proper sign extension needed for full compliance
        disp_len = 1u;
    } else if (mod_ == 2u) { // 16-bit displacement
        addr += ld16(pc + 2u);
        disp_len = 2u;
    }
    return ModRMResult(addr, disp_len);
}

// --- Opcode Execution ---
fn exec_one(s:ptr<function, VCPU>) -> bool {
  let pc = ( (*s).cs << 4u ) + lo16((*s).ip);
  let op = ld8(pc);
  var advanced = true;

  // Jcc rel8 (conditional jumps)
  if (op >= 0x70u && op <= 0x7Fu) {
    let cond = op & 0xFu;
    var jump = false;
    switch(cond) {
        case 0x2u: { jump = get_flag(s, FLAG_C); } // JB/JNAE
        case 0x3u: { jump = !get_flag(s, FLAG_C); } // JNB/JAE
        case 0x4u: { jump = get_flag(s, FLAG_Z); } // JZ/JE
        case 0x5u: { jump = !get_flag(s, FLAG_Z); } // JNZ/JNE
        case 0x8u: { jump = get_flag(s, FLAG_S); } // JS
        case 0x9u: { jump = !get_flag(s, FLAG_S); } // JNS
        default: {}
    }
    if (jump) {
        let rel = ld8(pc + 1u);
        // todo: sign extend
        (*s).ip = lo16((*s).ip + 2u + rel);
    } else {
        (*s).ip = lo16((*s).ip + 2u);
    }
  }
  // JMP rel8
  else if (op == 0xEBu) {
    let rel = ld8(pc + 1u);
    // todo: sign extend
    (*s).ip = lo16((*s).ip + 2u + rel);
  }
  // MOV r/m16, r16
  else if (op == 0x89u) {
    let modrm = decode_modrm(s, pc);
    let reg_val = 0u; // Simplified
    st16(modrm.addr, reg_val);
    (*s).ip = lo16((*s).ip + 2u + modrm.disp_len);
  }
  // MOV r16, r/m16
  else if (op == 0x8Bu) {
    let modrm = decode_modrm(s, pc);
    let mem_val = ld16(modrm.addr);
    // Simplified: store in AX
    (*s).ax = mem_val;
    (*s).ip = lo16((*s).ip + 2u + modrm.disp_len);
  }
  // MOV r16, imm16
  else if (op >= 0xB8u && op <= 0xBFu) {
      let reg_idx = op - 0xB8u;
      let val = ld16(pc + 1u);
      switch(reg_idx) {
          case 0u: { (*s).ax = val; }
          case 1u: { (*s).cx = val; }
          case 2u: { (*s).dx = val; }
          case 3u: { (*s).bx = val; }
          case 4u: { (*s).sp = val; }
          case 5u: { (*s).bp = val; }
          case 6u: { (*s).si = val; }
          case 7u: { (*s).di = val; }
          default: {}
      }
      (*s).ip = lo16((*s).ip + 3u);
  }
  // INT imm8
  else if (op == 0xCDu) {
    let vec = ld8(pc+1u);
    if (vec == 0x10u) { bios_int10((*s).ax); }
    else if (vec == 0x13u) { if (hi8((*s).ax) == 0x02u) { bios_int13((*s).ax, s); } }
    (*s).ip = lo16((*s).ip + 2u);
  }
  // LES r16, m16:16
  else if (op == 0xC4u) {
      let modrm = decode_modrm(s, pc);
      let modrm_byte = ld8(pc + 1u);
      let reg_idx = (modrm_byte >> 3u) & 0x07u;
      let mem_val = ld16(modrm.addr);
      let seg_val = ld16(modrm.addr + 2u);
      (*s).es = seg_val;
       switch(reg_idx) { //... update register
           default: {}
       }
      (*s).ip = lo16((*s).ip + 2u + modrm.disp_len);
  }
  // REP MOVSB
  else if (op == 0xF3u && ld8(pc+1u) == 0xA4u) {
      while(lo16((*s).cx) != 0u) {
          st8( (*s).es << 4u + lo16((*s).di), ld8( (*s).ds << 4u + lo16((*s).si) ) );
          (*s).si = lo16((*s).si + 1u); // CLD/STD not handled
          (*s).di = lo16((*s).di + 1u);
          (*s).cx = lo16((*s).cx - 1u);
      }
      (*s).ip = lo16((*s).ip + 2u);
  }
  // CLD
  else if (op == 0xFCu) {
      // Clear direction flag (TODO)
      (*s).ip = lo16((*s).ip + 1u);
  }
  // HLT
  else if (op == 0xF4u) {
    (*s).state = 0u;
    advanced = false;
  }
  // Fallback for other opcodes
  else {
    (*s).state = 0u;
    advanced = false;
  }

  return advanced;
}

// "hello MBR" seed: prints "GPU!" then HLT
fn seed_mbr(){
  var p:u32 = 0x7C00u;
  let b = array<u32,17u>(
    0xB8u,0x47u,0x00u,0xCDu,0x10u, // 'G'
    0xB8u,0x50u,0x00u,0xCDu,0x10u, // 'P'
    0xB8u,0x55u,0x00u,0xCDu,0x10u, // 'U'
    0xB8u,0x21u                    // '!'
  );
  for (var i:u32=0u; i<17u; i++){ st8(p+i, b[i]); }
  st8(p+17u,0xF4u); // HLT
  st8(p+510u, 0x55u); st8(p+511u, 0xAAu); // boot signature
}

@compute @workgroup_size(1)
fn hv_tick(@builtin(global_invocation_id) gid:vec3<u32>){
  if (gid.x != 0u) { return; } // 1 vCPU for now

  if (hv_state.stage == STAGE_INIT) {
    hv_state.console_base = 0xB8000u;
    hv_state.console_head = 0u;
    var s = hv_state.vcpu[0];
    s.cs = 0u; s.ip = 0x7C00u; s.ds=0u; s.es=0u; s.ss=0u;
    s.sp = 0x7C00u; s.state = 1u;
    hv_state.vcpu[0] = s;
    seed_mbr();
    hv_state.stage = STAGE_REALMODE;
  }

  var s0 = hv_state.vcpu[0];
  var i:u32 = 0u;
  loop {
    if (i >= io_header.steps_per_tick) { break; }
    if (s0.state == 0u) { break; }
    if (!exec_one(&s0)) { break; }
    i += 1u;
  }
  hv_state.vcpu[0] = s0;
}