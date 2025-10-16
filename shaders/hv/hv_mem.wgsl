// safe, bounded byte helpers on guest_ram
fn ram_len_words()->u32 { return arrayLength(&guest_ram); }

fn ld8(addr:u32)->u32{
  let i = addr >> 2u;
  let s = (addr & 3u) * 8u;
  if (i >= ram_len_words()) { return 0u; }
  return (guest_ram[i] >> s) & 0xFFu;
}
fn st8(addr:u32,v:u32){
  let i = addr >> 2u;
  let s = (addr & 3u) * 8u;
  if (i >= ram_len_words()) { return; }
  let m = ~(0xFFu << s);
  let old = guest_ram[i];
  guest_ram[i] = (old & m) | ((v & 0xFFu) << s);
}
fn ld16(a:u32)->u32{ return ld8(a) | (ld8(a+1u)<<8u); }
fn st16(a:u32,v:u32){ st8(a, v & 0xFFu); st8(a+1u, (v>>8u) & 0xFFu); }

// flat LBA sector read from ISO buffer (512B → RAM)
fn disk_len_words()->u32 { return arrayLength(&disk_iso); }

fn read_sector_lba(lba:u32, dst:u32){
  // ISO buffer is u32 words; each sector is 512 bytes = 128 words
  let base = lba * 128u;
  for (var i:u32=0u; i<128u; i++){
    if (base + i >= disk_len_words()) { break; }
    let w = disk_iso[base + i];
    let d = dst + i*4u;
    st8(d+0u,  w        & 0xFFu);
    st8(d+1u, (w>>8u)  & 0xFFu);
    st8(d+2u, (w>>16) & 0xFFu);
    st8(d+3u, (w>>24) & 0xFFu);
  }
}