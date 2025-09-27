"""
Generates the PixelText v1.1 demo cartridges.
"""

import os
import sys

# Add the project root to the Python path to allow importing from 'src'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lib import pixeltext

def generate_demo_cartridges():
    """
    Creates two demo PNG files in a 'demos' directory:
    1. hello_world.ptx.png: A simple UTF-8 string with minimal features.
    2. tech_spec.ptx.png: The full spec text, with all features enabled.
    """
    print("Generating PixelText v1.1 demo cartridges...")

    # Ensure the output directory exists
    output_dir = "demos"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Hello World Demo (Simple)
    hello_text = "Hello, PixelText v1.1 World! 🚀"
    hello_path = os.path.join(output_dir, "hello_world.ptx.png")
    print(f"Generating '{hello_path}' (simple encoding)...")
    pixeltext.encode(
        data=hello_text,
        output_path=hello_path,
        use_cbor=False,
        use_ecc=False,
        use_sync_markers=False
    )

    # 2. Tech Spec Demo (Full Features)
    spec_text = """
PixelText v1.1 (spec freeze)

## 0) Containers

* **Primary**: PNG (lossless).
* **Metadata**: PNG `iTXt` keys (see §5).
* **Pixel format**: RGBA8 preferred (RGB8 also OK).

---

## 1) Image layout (top → bottom)

```
Row 0..(Hh-1)  : Header band  (uncompressed, fixed size)
Row Hh..       : Payload tiles  (bytes→pixels; optional ECC; fiducials)
[optional]     : Font atlas (MSDF/MTSDF) packed below payload or separate asset
```

**Defaults**

* Header height `Hh = 1` row (16 RGBA pixels = 64 bytes).
* Tile size (payload area): **256×256 pixels**.
* Scan order: tiles **row-major**, pixels **row-major**.

---

## 2) Header band (binary layout, 64 bytes)

All integers big-endian.

| Off | Size | Field          | Notes                                      |
| --- | ---- | -------------- | ------------------------------------------ |
| 0   | 4    | magic          | `0x50 0x54 0x58 0x31` (“PTX1”)             |
| 4   | 2    | version        | `0x0001`                                   |
| 6   | 2    | header_px      | `0x0010` (16 RGBA pixels)                  |
| 8   | 4    | payload_len    | Byte length **before** ECC (post-compress) |
| 12  | 4    | flags          | Bitfield (see below)                       |
| 16  | 2    | tile_w         | Default 256                                |
| 18  | 2    | tile_h         | Default 256                                |
| 20  | 1    | rs_k           | Default 223 (RS data symbols)              |
| 21  | 1    | rs_n           | Default 255 (RS total symbols)             |
| 22  | 2    | reserved       | `0x0000`                                   |
| 24  | 4    | crc32c_payload | CRC32C of compressed payload bytes         |
| 28  | 4    | crc32c_header  | CRC32C of bytes [0..27]                    |
| 32  | 16   | sha256_lo      | First 16 bytes of full SHA-256 (optional)  |
| 48  | 16   | sha256_hi      | Last 16 bytes (optional; may be zero)      |

**Flags (bitfield)**

* `0`: ENCODING_UTF8 (else CBOR)
* `1`: ENCODING_CBOR
* `8`: COMP_ZLIB
* `9`: COMP_ZSTD
* `16`: ECC_RS_PRESENT
* `17`: SYNC_MARKERS_PRESENT
* `24`: ALPHA_PARITY (A = R⊕G⊕B per-pixel)
* (other bits reserved; must be 0)

> **Rule**: Exactly one of bits 0/1 **must** be set; exactly one of bits 8/9 **may** be set.
"""
    spec_data = {
        "title": "PixelText v1.1 Specification",
        "version": "1.1",
        "content": spec_text
    }
    spec_path = os.path.join(output_dir, "tech_spec.ptx.png")
    print(f"Generating '{spec_path}' (full feature encoding)...")
    pixeltext.encode(
        data=spec_data,
        output_path=spec_path,
        use_cbor=True,
        use_ecc=True,
        use_sync_markers=True
    )

    print("\nDemo cartridges generated successfully in 'demos/' directory.")
    print("You can now inspect these PNG files.")

if __name__ == "__main__":
    generate_demo_cartridges()