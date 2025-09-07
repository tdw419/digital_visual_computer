import os
import struct
import zlib
from pathlib import Path


def _crc(chunk_type: bytes, data: bytes) -> int:
    import binascii
    return binascii.crc32(chunk_type + data) & 0xFFFFFFFF


def _chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", _crc(chunk_type, data))
    )


def write_simple_2x2_png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    # PNG signature
    png_sig = b"\x89PNG\r\n\x1a\n"

    # IHDR: width=2, height=2, bit depth=8, color type=2 (RGB), compression=0, filter=0, interlace=0
    ihdr = struct.pack(
        ">IIBBBBB",
        2,  # width
        2,  # height
        8,  # bit depth
        2,  # color type (Truecolor RGB)
        0,  # compression
        0,  # filter
        0,  # interlace
    )

    # Scanlines (each begins with filter type 0)
    # Row 0 (top): Red (255,0,0), Green (0,255,0)
    scanline0 = bytes([0, 255, 0, 0, 0, 255, 0])
    # Row 1 (bottom): Blue (0,0,255), White (255,255,255)
    scanline1 = bytes([0, 0, 0, 255, 255, 255, 255])
    raw = scanline0 + scanline1
    idat_data = zlib.compress(raw)

    png = (
        png_sig
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat_data)
        + _chunk(b"IEND", b"")
    )

    with open(path, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    out_path = Path("tests/color_lang/fixtures/simple_2x2.png").resolve()
    write_simple_2x2_png(out_path)
    print(f"Wrote {out_path}")

