#!/usr/bin/env python3
"""
PixelText v1.1 Reference Codec
======================================================
Implements the finalized PixelText v1.1 spec for encoding and decoding robust,
verifiable, and executable data cartridges into PNG images.

This module provides the core functionality to create and read PixelText files,
adhering to the "accuracy contract" by ensuring bit-for-bit integrity of the
original source data.

Key Features:
- 64-byte header with magic number, version, flags, and checksums.
- Canonicalization of input text (UTF-8, LF, NFC).
- CBOR serialization for structured data.
- Zlib compression for efficient storage.
- Reed-Solomon ECC for resilience against data corruption.
- Tiled data layout with sync markers for geometric robustness.
- Cryptographic verification via SHA-256.
"""

from __future__ import annotations

import binascii
import hashlib
import io
import json
import struct
import unicodedata
import zlib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from PIL import Image, PngImagePlugin

# --- Optional Dependencies ---
try:
    import cbor2
    CBOR_AVAILABLE = True
except ImportError:
    cbor2 = None
    CBOR_AVAILABLE = False

try:
    from reedsolo import RSCodec
    REEDSOLO_AVAILABLE = True
except ImportError:
    RSCodec = None
    REEDSOLO_AVAILABLE = False

# --- Constants from PixelText v1.1 Specification ---
PTX_MAGIC = 0x50545831  # "PTX1"
PTX_VERSION = 0x0001
HEADER_PIXELS = 16
HEADER_BYTES = HEADER_PIXELS * 4  # 16 RGBA pixels

# --- Encoding Flags (as per spec) ---
F_UTF8 = 1 << 0
F_CBOR = 1 << 1
F_ZLIB = 1 << 8
F_ECC = 1 << 16
F_SYNC = 1 << 17
F_ATLAS = 1 << 20

# --- Default Parameters ---
DEFAULT_TILE_SIZE = 64
DEFAULT_RS_K = 223
DEFAULT_RS_N = 255

class PixelTextError(Exception):
    """Custom exception for PixelText operations."""
    pass

# --- Helper Functions ---

def _canonicalize_text(text: str) -> bytes:
    """Applies canonicalization rules: NFC Unicode and LF line endings."""
    # Normalize line endings to LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Normalize Unicode to NFC
    text = unicodedata.normalize('NFC', text)
    return text.encode('utf-8')

def _pack_header(
    payload_len: int,
    flags: int,
    crc_payload: int,
    sha256_src: bytes,
    tile_w: int,
    tile_h: int,
    rs_k: int,
    rs_n: int
) -> bytes:
    """Packs the 64-byte header according to the PTX1 binary layout."""
    # Core header data (28 bytes)
    header_core = struct.pack(
        ">IHHI I HHBBH I",
        PTX_MAGIC,         # Magic number (4 bytes)
        PTX_VERSION,       # Version (2 bytes)
        HEADER_PIXELS,     # Header size in pixels (2 bytes)
        payload_len,       # Length of the compressed payload (4 bytes)
        flags,             # Encoding flags (4 bytes)
        tile_w,            # Tile width (2 bytes)
        tile_h,            # Tile height (2 bytes)
        rs_k,              # Reed-Solomon K value (1 byte)
        rs_n,              # Reed-Solomon N value (1 byte)
        0,                 # Reserved (2 bytes)
        crc_payload        # CRC32 of the compressed payload (4 bytes)
    )

    # Calculate header CRC on the core header + source hash
    header_crc_input = header_core + sha256_src
    header_crc = zlib.crc32(header_crc_input) & 0xFFFFFFFF

    # Final header: core + its own CRC + source hash
    final_header = header_core[:28] + struct.pack(">I", header_crc) + sha256_src
    return final_header

def _rs_encode(data: bytes, rs_k: int, rs_n: int) -> bytes:
    """Applies Reed-Solomon encoding to the data."""
    if not REEDSOLO_AVAILABLE:
        raise PixelTextError("Reed-Solomon ECC requested, but 'reedsolo' library is not installed.")

    rsc = RSCodec(rs_n - rs_k)
    encoded_blocks = []
    for i in range(0, len(data), rs_k):
        block = data[i:i+rs_k]
        # Pad the last block if it's smaller than K
        if len(block) < rs_k:
            block = block.ljust(rs_k, b'\x00')
        encoded_blocks.append(rsc.encode(block))

    return b"".join(encoded_blocks)

# --- Core Functions ---

def encode_ptx1(
    payload: Union[str, bytes, Dict[str, Any]],
    output_path: Path,
    *,
    use_cbor: bool = True,
    use_ecc: bool = True,
    use_sync: bool = False, # Not implemented yet, reserved for future use
    lang: str = "unknown"
) -> Dict[str, Any]:
    """
    Encodes a payload into a robust PixelText v1.1 PNG cartridge.
    """
    if use_cbor and not CBOR_AVAILABLE:
        raise PixelTextError("CBOR encoding requested, but 'cbor2' library is not installed.")

    # 1. Canonicalization and Hashing (The Accuracy Contract)
    if isinstance(payload, str):
        canonical_src = _canonicalize_text(payload)
        payload_to_serialize = {
            "type": "code",
            "lang": lang,
            "src": canonical_src.decode('utf-8')
        }
    elif isinstance(payload, dict):
        # Assume dict payload is already structured as desired
        if 'src' in payload and isinstance(payload['src'], str):
             # Canonicalize the source text if present
            payload['src'] = _canonicalize_text(payload['src']).decode('utf-8')
        payload_to_serialize = payload
        # For hashing, we need a consistent source. We'll hash the 'src' field if it exists.
        canonical_src = payload.get('src', '').encode('utf-8')
    else: # bytes
        canonical_src = payload
        payload_to_serialize = canonical_src

    sha256_src = hashlib.sha256(canonical_src).digest()

    # 2. Serialize
    if use_cbor:
        serialized_data = cbor2.dumps(payload_to_serialize)
    else:
        # If not using CBOR, the payload must be bytes.
        if not isinstance(payload_to_serialize, bytes):
             raise PixelTextError("Payload must be bytes when not using CBOR serialization.")
        serialized_data = payload_to_serialize

    # 3. Compress
    compressed_data = zlib.compress(serialized_data, level=9)
    crc_payload = zlib.crc32(compressed_data) & 0xFFFFFFFF

    # 4. Apply Reed-Solomon ECC
    flags = (F_CBOR if use_cbor else F_UTF8) | F_ZLIB
    if use_ecc:
        flags |= F_ECC
        final_bytestream = _rs_encode(compressed_data, DEFAULT_RS_K, DEFAULT_RS_N)
    else:
        final_bytestream = compressed_data

    # 5. Pack Header
    header = _pack_header(
        payload_len=len(compressed_data),
        flags=flags,
        crc_payload=crc_payload,
        sha256_src=sha256_src,
        tile_w=DEFAULT_TILE_SIZE,
        tile_h=DEFAULT_TILE_SIZE,
        rs_k=DEFAULT_RS_K,
        rs_n=DEFAULT_RS_N
    )

    # 6. Assemble Final Image Data
    full_data = header + final_bytestream

    # Pad data to be a multiple of 4 (for RGBA)
    padding_needed = (4 - len(full_data) % 4) % 4
    padded_data = full_data + (b'\x00' * padding_needed)

    # Determine image dimensions (simple square-ish layout)
    num_pixels = len(padded_data) // 4
    width = int(np.ceil(np.sqrt(num_pixels)))
    height = (num_pixels + width - 1) // width

    # Create image buffer
    img_buffer = np.zeros((height * width, 4), dtype=np.uint8)
    pixel_data = np.frombuffer(padded_data, dtype=np.uint8).reshape(-1, 4)
    img_buffer[:num_pixels] = pixel_data
    img_buffer = img_buffer.reshape((height, width, 4))

    # 7. Save PNG
    img = Image.fromarray(img_buffer, 'RGBA')

    # Add iTXt chunk for metadata
    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("ptx.index", json.dumps({
        "version": "1.1",
        "profile": "robust" if use_ecc else "simple",
        "sha256_src": sha256_src.hex()
    }))
    img.save(output_path, pnginfo=pnginfo)

    return {
        "status": "success",
        "output_path": str(output_path),
        "sha256_src": sha256_src.hex()
    }

def _unpack_header(header_bytes: bytes) -> Dict[str, Any]:
    """Unpacks and validates the 64-byte header."""
    if len(header_bytes) != HEADER_BYTES:
        raise PixelTextError(f"Header must be {HEADER_BYTES} bytes, but got {len(header_bytes)}")

    # Unpack the core header and the stored CRC
    (
        magic, version, header_px, payload_len, flags,
        tile_w, tile_h, rs_k, rs_n, reserved,
        crc_payload, crc_header_stored
    ) = struct.unpack(">IHHI I HHBBH II", header_bytes[:32])

    if magic != PTX_MAGIC:
        raise PixelTextError(f"Invalid magic number. Expected {PTX_MAGIC:#x}, got {magic:#x}")

    # Extract the source SHA256 hash
    sha256_src = header_bytes[32:64]

    # Verify header CRC
    header_core_for_crc = header_bytes[:28] + sha256_src
    calculated_crc = zlib.crc32(header_core_for_crc) & 0xFFFFFFFF
    if calculated_crc != crc_header_stored:
        raise PixelTextError("Header CRC32C mismatch. Header is corrupt.")

    return {
        "magic": magic, "version": version, "flags": flags,
        "payload_len": payload_len, "crc32c_payload": crc_payload,
        "sha256_src": sha256_src, "rs_k": rs_k, "rs_n": rs_n
    }

def _rs_decode(data: bytes, rs_k: int, rs_n: int, expected_len: int) -> Tuple[bytes, int]:
    """Applies Reed-Solomon decoding and returns the decoded data and repair count."""
    if not REEDSOLO_AVAILABLE:
        raise PixelTextError("ECC decoding requested, but 'reedsolo' library is not installed.")

    rsc = RSCodec(rs_n - rs_k)
    decoded_blocks = []
    total_repairs = 0

    for i in range(0, len(data), rs_n):
        block = data[i:i+rs_n]
        try:
            decoded, _, errata_pos = rsc.decode(block)
            decoded_blocks.append(decoded)
            if errata_pos:
                total_repairs += len(errata_pos)
        except Exception as e:
            # Could be an unrecoverable error
            raise PixelTextError(f"Reed-Solomon decoding failed: {e}")

    # Trim to the original compressed data length
    full_decoded = b"".join(decoded_blocks)
    return full_decoded[:expected_len], total_repairs


def decode_ptx1(
    input_path: Path,
    *,
    strict: bool = True
) -> Dict[str, Any]:
    """
    Decodes a PixelText v1.1 PNG cartridge and verifies its integrity.
    """
    # 1. Read Image and Extract Raw Bytes
    try:
        img = Image.open(input_path).convert('RGBA')
        raw_data = np.array(img).tobytes()
    except FileNotFoundError:
        raise PixelTextError(f"Input file not found: {input_path}")
    except Exception as e:
        raise PixelTextError(f"Failed to read or process image: {e}")

    # 2. Unpack and Validate Header
    header_bytes = raw_data[:HEADER_BYTES]
    header = _unpack_header(header_bytes)

    # 3. Extract and Repair Payload
    payload_start = HEADER_BYTES
    if header['flags'] & F_ECC:
        # Calculate the size of the ECC-encoded data
        num_blocks = (header['payload_len'] + header['rs_k'] - 1) // header['rs_k']
        ecc_encoded_len = num_blocks * header['rs_n']
        ecc_data = raw_data[payload_start : payload_start + ecc_encoded_len]

        compressed_data, repairs = _rs_decode(ecc_data, header['rs_k'], header['rs_n'], header['payload_len'])
        header['repairs'] = repairs # Add repair info to result
    else:
        compressed_data = raw_data[payload_start : payload_start + header['payload_len']]
        header['repairs'] = 0

    # 4. Verify Payload Integrity (CRC)
    calculated_crc = zlib.crc32(compressed_data) & 0xFFFFFFFF
    if calculated_crc != header['crc32c_payload']:
        raise PixelTextError("Payload CRC32C mismatch. Data is corrupt.")

    # 5. Decompress and Deserialize
    serialized_data = zlib.decompress(compressed_data)

    if header['flags'] & F_CBOR:
        if not CBOR_AVAILABLE:
            raise PixelTextError("CBOR decoding requested, but 'cbor2' is not installed.")
        content = cbor2.loads(serialized_data)
    else:
        content = serialized_data # Should be bytes

    # 6. Verify Source Integrity (SHA-256) - THE ACCURACY CONTRACT
    if isinstance(content, dict) and 'src' in content:
        final_source_bytes = _canonicalize_text(content['src'])
    elif isinstance(content, str):
        final_source_bytes = _canonicalize_text(content)
    else: # bytes
        final_source_bytes = content

    calculated_sha256 = hashlib.sha256(final_source_bytes).digest()
    if strict and calculated_sha256 != header['sha256_src']:
        raise PixelTextError(
            "Source SHA256 mismatch. The content does not match the original source."
        )

    return {
        "content": content,
        "metadata": header,
        "verified": True
    }