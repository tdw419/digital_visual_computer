"""
PixelText v1.1 Decoder
"""

import zlib
from typing import Union, Dict, Any

import cbor2
import numpy as np
from PIL import Image
from reedsolo import RSCodec, ReedSolomonError
from crc32c import crc32c

from .header import PixelTextHeader, HeaderFlags, HEADER_BYTE_SIZE

def decode(image_or_path: Union[str, Image.Image]) -> Union[str, bytes, Dict[str, Any]]:
    """
    Decodes a PixelText v1.1 PNG image.

    Args:
        image_or_path: Path to the PNG file or a PIL Image object.

    Returns:
        The decoded data in its original format (str, bytes, or dict).
    """
    if isinstance(image_or_path, (str, bytes, bytearray)) or hasattr(image_or_path, "read"):
        img = Image.open(image_or_path)
    else:
        img = image_or_path

    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    pixel_array = np.array(img)

    # 1. Read and Unpack Header
    img_h, img_w, bytes_per_pixel = pixel_array.shape

    # Read the raw bytes of the entire image
    raw_bytes = pixel_array.tobytes()

    # Extract the 64-byte header from the beginning of the bytestream
    if len(raw_bytes) < HEADER_BYTE_SIZE:
        raise ValueError("Image is too small to contain a PixelText header.")
    header = PixelTextHeader.unpack(raw_bytes[:HEADER_BYTE_SIZE])

    # 2. Extract Payload from Tiles
    ecc_payload_bytes = bytearray()

    tile_w, tile_h = header.tile_w, header.tile_h
    marker_byte_size = 16 if (header.flags & HeaderFlags.SYNC_MARKERS_PRESENT) else 0

    # Calculate header height in rows, and tile grid dimensions
    header_h = (HEADER_BYTE_SIZE + (img_w * bytes_per_pixel) - 1) // (img_w * bytes_per_pixel)
    tiles_across = img_w // tile_w
    tiles_down = (img_h - header_h) // tile_h
    num_tiles = tiles_across * tiles_down

    for i in range(num_tiles):
        tile_y = header_h + (i // tiles_across) * tile_h
        tile_x = (i % tiles_across) * tile_w

        tile_pixel_array = pixel_array[tile_y:tile_y+tile_h, tile_x:tile_x+tile_w]

        if header.flags & HeaderFlags.SYNC_MARKERS_PRESENT:
            # Validate the fiducial marker
            marker = tile_pixel_array[0:2, 0:2]
            expected_marker = np.frombuffer(
                bytes([0xDE,0xAD,0xBE,0xEF, 0xFA,0xCE,0xB0,0x0C, 0xFE,0xED,0xFA,0xCE, 0xC0,0xDE,0xC0,0xDE]),
                dtype=np.uint8
            ).reshape(2, 2, 4)
            if not np.array_equal(marker, expected_marker):
                raise ValueError(f"Invalid fiducial marker found in tile {i}. Data is likely corrupt or misaligned.")

            # Use a boolean mask to extract data, avoiding the marker
            # This is cleaner than manual byte slicing.
            mask = np.ones(tile_pixel_array.shape[:2], dtype=bool)
            mask[0:2, 0:2] = False
            data_pixels = tile_pixel_array[mask]
            ecc_payload_bytes.extend(data_pixels.tobytes())
        else:
            ecc_payload_bytes.extend(tile_pixel_array.tobytes())

    # Truncate to the actual payload size, as padding might be included
    # The length of the ECC payload is not stored directly. We must decode it
    # and then truncate based on the compressed_payload length from the header.

    # 3. Error Correction
    if header.flags & HeaderFlags.ECC_RS_PRESENT:
        rs = RSCodec(nsym=header.rs_n - header.rs_k)

        block_size = header.rs_n
        corrected_payload = bytearray()

        for i in range(0, len(ecc_payload_bytes), block_size):
            block = ecc_payload_bytes[i:i+block_size]
            try:
                # The `decode` function expects a bytes-like object
                decoded_block = rs.decode(bytes(block))
                corrected_payload.extend(decoded_block[0]) # result is (data, ecc)
            except ReedSolomonError:
                # Handle corrupted block - for now, we fail.
                # A more robust implementation might try to return partial data.
                raise ValueError(f"Reed-Solomon decoding failed on block {i // block_size}. Data is too corrupt.")

        compressed_payload = bytes(corrected_payload)
    else:
        compressed_payload = bytes(ecc_payload_bytes)

    # 4. Truncate and Verify Payload
    compressed_payload = compressed_payload[:header.payload_len]

    calculated_crc = crc32c(compressed_payload)
    if calculated_crc != header.crc32c_payload:
        raise ValueError(f"Payload CRC mismatch. Expected {header.crc32c_payload}, got {calculated_crc}")

    # 5. Decompression
    if header.flags & HeaderFlags.COMP_ZLIB:
        payload = zlib.decompress(compressed_payload)
    else:
        payload = compressed_payload

    # 6. Deserialization
    if header.flags & HeaderFlags.ENCODING_CBOR:
        return cbor2.loads(payload)
    elif header.flags & HeaderFlags.ENCODING_UTF8:
        return payload.decode('utf-8')
    else:
        # Fallback for raw bytes if no encoding flag is set (should not happen with spec v1.1)
        return payload