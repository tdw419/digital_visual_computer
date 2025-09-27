"""
PixelText v1.1 Header Module
Handles packing and unpacking of the 64-byte header.
"""

import struct
from dataclasses import dataclass
from crc32c import crc32c

# Constants from the specification
MAGIC_NUMBER = b'PTX1'
HEADER_PX_SIZE = 16  # 16 RGBA pixels = 64 bytes
HEADER_BYTE_SIZE = HEADER_PX_SIZE * 4

# --- Flag Bitfield Definitions ---
class HeaderFlags:
    ENCODING_UTF8 = 1 << 0
    ENCODING_CBOR = 1 << 1
    COMP_ZLIB = 1 << 8
    COMP_ZSTD = 1 << 9
    ECC_RS_PRESENT = 1 << 16
    SYNC_MARKERS_PRESENT = 1 << 17
    ALPHA_PARITY = 1 << 24

@dataclass
class PixelTextHeader:
    """A dataclass representing the parsed PixelText header."""
    magic: bytes = MAGIC_NUMBER
    version: int = 1
    header_px: int = HEADER_PX_SIZE
    payload_len: int = 0
    flags: int = 0
    tile_w: int = 256
    tile_h: int = 256
    rs_k: int = 223
    rs_n: int = 255
    reserved: int = 0
    crc32c_payload: int = 0
    crc32c_header: int = 0
    sha256_lo: bytes = b'\x00' * 16
    sha256_hi: bytes = b'\x00' * 16

    def pack(self) -> bytes:
        """Packs the header into a 64-byte buffer."""
        # Pack the first 24 bytes
        part1 = struct.pack(
            '>4sHHIIHHBBH',
            self.magic, self.version, self.header_px,
            self.payload_len, self.flags,
            self.tile_w, self.tile_h,
            self.rs_k, self.rs_n, self.reserved
        )
        # Add the 4-byte payload CRC
        part2 = self.crc32c_payload.to_bytes(4, 'big')

        # Calculate header CRC on the first 28 bytes ([0..27])
        header_data_for_crc = part1 + part2
        self.crc32c_header = crc32c(header_data_for_crc)

        # Construct the full 64-byte header
        full_header_bytes = (
            header_data_for_crc +
            self.crc32c_header.to_bytes(4, 'big') +
            self.sha256_lo +
            self.sha256_hi
        )
        return full_header_bytes

    @classmethod
    def unpack(cls, buffer: bytes) -> "PixelTextHeader":
        """Unpacks a 64-byte buffer into a PixelTextHeader object."""
        if len(buffer) != HEADER_BYTE_SIZE:
            raise ValueError(f"Header buffer must be {HEADER_BYTE_SIZE} bytes long, but got {len(buffer)}")

        # Unpack all fields first
        magic, version, header_px, payload_len, flags, tile_w, tile_h, rs_k, rs_n, reserved, crc32c_payload, crc32c_header, sha256_lo, sha256_hi = struct.unpack(
            '>4sHHIIHHBBHII16s16s',
            buffer
        )

        if magic != MAGIC_NUMBER:
            raise ValueError(f"Invalid magic number. Expected {MAGIC_NUMBER}, got {magic}")

        if version != 1:
            raise ValueError(f"Unsupported version. Expected 1, got {version}")

        # Verify header CRC on the first 28 bytes ([0..27])
        header_data_for_crc = buffer[0:28]
        calculated_crc = crc32c(header_data_for_crc)
        if calculated_crc != crc32c_header:
            raise ValueError(f"Header CRC mismatch. Expected {crc32c_header}, got {calculated_crc}")


        return cls(
            magic=magic,
            version=version,
            header_px=header_px,
            payload_len=payload_len,
            flags=flags,
            tile_w=tile_w,
            tile_h=tile_h,
            rs_k=rs_k,
            rs_n=rs_n,
            reserved=reserved,
            crc32c_payload=crc32c_payload,
            crc32c_header=crc32c_header,
            sha256_lo=sha256_lo,
            sha256_hi=sha256_hi,
        )