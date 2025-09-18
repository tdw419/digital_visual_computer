#!/usr/bin/env python3
# scripts/pxrom.py
# Pixel ROM encoder/decoder with resume + progress + reusable frame parser.
# Usage (encode):
#   python3 scripts/pxrom.py encode <input> --out artifacts/px --tiles 128x72 --tile-size 8 --jobs 4 --compress-level 1 --resume
# Usage (decode):
#   python3 scripts/pxrom.py decode artifacts/px --out out.iso --tiles 128x72 --tile-size 8
import argparse, hashlib, json, math, os, re, sys, zlib
from pathlib import Path
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

MAGIC = b"PXROM1\0\0"  # 8 bytes
HEADER_LEN = 24         # bytes, fixed in our format

def _tile_indices(tiles_x, tiles_y):
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            yield (tx, ty)

def _pack_header(frame_idx, total_frames, payload_len, payload_crc32):
    """
    24 bytes total:
    0..7    MAGIC (8)
    8..11   frame_idx (u32 LE)
    12..15  total_frames (u32 LE)
    16..19  payload_len (u32 LE)
    20..23  payload_crc32 (u32 LE)
    """
    def u32(n): return n.to_bytes(4, "little", signed=False)
    return MAGIC + u32(frame_idx) + u32(total_frames) + u32(payload_len) + u32(payload_crc32)

def _unpack_header(b):
    assert len(b) >= HEADER_LEN
    if b[:8] != MAGIC:
        raise ValueError("Bad MAGIC")
    def u32_at(off): return int.from_bytes(b[off:off+4], "little", signed=False)
    return {
        "frame_idx": u32_at(8),
        "total_frames": u32_at(12),
        "payload_len": u32_at(16),
        "payload_crc32": u32_at(20),
    }

def _rgb_bytes_to_png(data_bytes, tiles_x, tiles_y, tile_size, out_path):
    # bytes → tiles (3 bytes per tile) with header occupying first 8 tiles (8*3=24 bytes)
    tile_cap = tiles_x * tiles_y
    need = math.ceil(len(data_bytes) / 3)
    if need > tile_cap:
        raise ValueError("Data too large for one frame.")

    img_w = tiles_x * tile_size
    img_h = tiles_y * tile_size
    im = Image.new("RGB", (img_w, img_h), (0, 0, 0))
    pix = im.load()

    # blit tiles as solid rectangles (fast)
    it = iter(data_bytes)
    ti = 0
    for (tx, ty) in _tile_indices(tiles_x, tiles_y):
        if ti >= need:
            break
        r = next(it, 0)
        g = next(it, 0)
        b = next(it, 0)
        x0 = tx * tile_size
        y0 = ty * tile_size
        for yy in range(y0, y0 + tile_size):
            for xx in range(x0, x0 + tile_size):
                pix[xx, yy] = (r, g, b)
        ti += 1

    im.save(out_path, format="PNG", optimize=False, compress_level=im.info.get("compress_level", 1))

def _png_to_rgb_bytes(im, tiles_x, tiles_y, tile_size):
    # read center of each tile in scan order
    im = im.convert("RGB")
    pix = im.load()
    out = bytearray()
    for (tx, ty) in _tile_indices(tiles_x, tiles_y):
        cx = tx * tile_size + tile_size // 2
        cy = ty * tile_size + tile_size // 2
        r, g, b = pix[cx, cy]
        out.extend((r, g, b))
    return bytes(out)

def parse_frame_image(im, tiles_x, tiles_y, tile_size):
    """
    Reusable: returns (hdr_dict, payload_bytes)
    """
    raw = _png_to_rgb_bytes(im, tiles_x, tiles_y, tile_size)
    header = _unpack_header(raw[:HEADER_LEN])
    payload = raw[HEADER_LEN:HEADER_LEN + header["payload_len"]]
    if zlib.crc32(payload) & 0xFFFFFFFF != header["payload_crc32"]:
        raise ValueError(f"CRC mismatch in frame {header['frame_idx']}")
    return header, payload

def parse_frame_path(path, tiles_x, tiles_y, tile_size):
    im = Image.open(path)
    try:
        return parse_frame_image(im, tiles_x, tiles_y, tile_size)
    finally:
        im.close()

def _chunks(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i:i+size]

def _existing_indices(out_dir: Path):
    idx = set()
    for p in out_dir.glob("pxrom_*.png"):
        m = re.match(r"pxrom_(\d{6})\.png$", p.name)
        if m:
            idx.add(int(m.group(1)))
    return idx

def _encode_one_frame(args):
    (frame_idx, total_frames, payload, tiles_x, tiles_y, tile_size, compress_level, out_dir_str) = args
    out_dir = Path(out_dir_str)
    out_path = out_dir / f"pxrom_{frame_idx:06d}.png"
    header = _pack_header(frame_idx, total_frames, len(payload), zlib.crc32(payload) & 0xFFFFFFFF)
    data = header + payload
    img_w = tiles_x * tile_size
    img_h = tiles_y * tile_size
    # pass compress level via PNG info
    Image.Image.info = {"compress_level": compress_level}
    _rgb_bytes_to_png(data, tiles_x, tiles_y, tile_size, out_path)
    return frame_idx

def encode_file_to_pxrom(in_path: Path, out_dir: Path, tiles_x: int, tiles_y: int, tile_size: int,
                         jobs: int = 1, compress_level: int = 1, resume: bool = False, progress: bool = True):
    out_dir.mkdir(parents=True, exist_ok=True)
    data = in_path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()

    bytes_per_frame = tiles_x * tiles_y * 3 - HEADER_LEN
    if bytes_per_frame <= 0:
        raise ValueError("Grid too small for header.")
    chunks = list(_chunks(data, bytes_per_frame))
    total_frames = len(chunks)

    existing = _existing_indices(out_dir) if resume else set()
    todo = [i for i in range(total_frames) if i not in existing]
    skipped = len(existing & set(range(total_frames)))

    if progress:
        print(f"[pxrom] {in_path.name}: {len(data)/1_048_576:.2f} MiB; frames={total_frames}; bytes/frame={bytes_per_frame}")
        if resume:
            print(f"[pxrom] resume: {skipped} already present, {len(todo)} to encode")

    if jobs > 1 and len(todo) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futs = []
            for i in todo:
                args = (i, total_frames, chunks[i], tiles_x, tiles_y, tile_size, compress_level, str(out_dir))
                futs.append(ex.submit(_encode_one_frame, args))
            done = 0
            for f in as_completed(futs):
                f.result()
                done += 1
                if progress and (done % max(1, total_frames // 100) == 0):
                    print(f"[pxrom] progress {done+skipped}/{total_frames}")
    else:
        for i in todo:
            _encode_one_frame((i, total_frames, chunks[i], tiles_x, tiles_y, tile_size, compress_level, str(out_dir)))
            if progress and (i % max(1, total_frames // 100) == 0):
                print(f"[pxrom] progress {i+1}/{total_frames}")

    manifest = {
        "input": str(in_path),
        "tiles": [tiles_x, tiles_y],
        "tile_size": tile_size,
        "bytes_per_frame": bytes_per_frame,
        "total_frames": total_frames,
        "sha256": sha256,
        "skipped_frames": skipped,
        "frames_dir": str(out_dir),
    }
    (out_dir / "pxrom_manifest.json").write_text(json.dumps(manifest, indent=2))
    if progress:
        print(f"[pxrom] Wrote manifest: {out_dir/'pxrom_manifest.json'}")
        print(f"[pxrom] Frames dir: {out_dir} (count: {total_frames})")

def decode_pxrom_dir(in_dir: Path, out_path: Path, tiles_x: int, tiles_y: int, tile_size: int):
    # sorted by index
    frames = sorted([p for p in in_dir.glob("pxrom_*.png")])
    if not frames:
        raise SystemExit("No frames found.")
    payloads = {}
    total = None
    for p in frames:
        hdr, payload = parse_frame_path(p, tiles_x, tiles_y, tile_size)
        if total is None:
            total = hdr["total_frames"]
        if hdr["total_frames"] != total:
            raise ValueError("Inconsistent total_frames across frames.")
        payloads[hdr["frame_idx"]] = payload
    out = bytearray()
    for i in range(total):
        if i not in payloads:
            raise ValueError(f"Missing frame {i}")
        out.extend(payloads[i])
    out_path.write_bytes(bytes(out))
    print(f"[pxrom] Wrote reconstructed file: {out_path}")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    enc = sub.add_parser("encode")
    enc.add_argument("input")
    enc.add_argument("--out", required=True)
    enc.add_argument("--tiles", required=True, help="WxH, e.g. 128x72")
    enc.add_argument("--tile-size", type=int, required=True)
    enc.add_argument("--jobs", type=int, default=1)
    enc.add_argument("--compress-level", type=int, default=1)
    enc.add_argument("--resume", action="store_true")
    enc.add_argument("--no-progress", action="store_true")

    dec = sub.add_parser("decode")
    dec.add_argument("frames_dir")
    dec.add_argument("--out", required=True)
    dec.add_argument("--tiles", required=True)
    dec.add_argument("--tile-size", type=int, required=True)

    args = ap.parse_args()
    if args.cmd == "encode":
        tiles_x, tiles_y = map(int, args.tiles.lower().split("x"))
        encode_file_to_pxrom(
            Path(args.input),
            Path(args.out),
            tiles_x, tiles_y,
            args.tile_size,
            jobs=args.jobs,
            compress_level=args.compress_level,
            resume=args.resume,
            progress=not args.no_progress
        )
    elif args.cmd == "decode":
        tiles_x, tiles_y = map(int, args.tiles.lower().split("x"))
        decode_pxrom_dir(Path(args.frames_dir), Path(args.out), tiles_x, tiles_y, args.tile_size)

if __name__ == "__main__":
    main()
