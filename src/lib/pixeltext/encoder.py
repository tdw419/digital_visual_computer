"""
PixelText v1.1 Encoder
"""

import zlib
import json
from typing import Union, Optional, Dict, Any

import cbor2
import numpy as np
from PIL import Image, PngImagePlugin
from reedsolo import RSCodec
from crc32c import crc32c

from .header import PixelTextHeader, HeaderFlags, HEADER_BYTE_SIZE

# Fiducial marker pattern (top-left 2x2 pixels of a tile)
# Values from the specification.
FIDUCIAL_MARKER_BYTES = bytes([
    0xDE, 0xAD, 0xBE, 0xEF, 0xFA, 0xCE, 0xB0, 0x0C,
    0xFE, 0xED, 0xFA, 0xCE, 0xC0, 0xDE, 0xC0, 0xDE
])
FIDUCIAL_MARKER_PIXELS = np.frombuffer(FIDUCIAL_MARKER_BYTES, dtype=np.uint8).reshape(2, 2, 4)


def encode(
    data: Union[str, bytes, Dict[str, Any]],
    output_path: Optional[str] = None,
    use_cbor: bool = True,
    use_ecc: bool = True,
    use_sync_markers: bool = True,
) -> Image.Image:
    """
    Encodes data into a PixelText v1.1 PNG image.

    Args:
        data: The data to encode. Can be a string, bytes, or a dictionary (for CBOR).
        output_path: If provided, saves the resulting PNG to this path.
        use_cbor: If True, wraps the data in a CBOR object.
        use_ecc: If True, applies Reed-Solomon error correction.
        use_sync_markers: If True, adds fiducial markers to each tile.

    Returns:
        A PIL.Image.Image object containing the encoded data.
    """
    header = PixelTextHeader()

    # 1. Data Preparation
    if isinstance(data, dict) or use_cbor:
        payload = cbor2.dumps(data)
        header.flags |= HeaderFlags.ENCODING_CBOR
    elif isinstance(data, str):
        payload = data.encode('utf-8')
        header.flags |= HeaderFlags.ENCODING_UTF8
    elif isinstance(data, bytes):
        payload = data
        header.flags |= HeaderFlags.ENCODING_UTF8 # Assume UTF-8 for raw bytes for now
    else:
        raise TypeError("Unsupported data type. Must be str, bytes, or dict.")

    # 2. Compression
    compressed_payload = zlib.compress(payload, level=9)
    header.flags |= HeaderFlags.COMP_ZLIB
    header.payload_len = len(compressed_payload)
    header.crc32c_payload = crc32c(compressed_payload)

    # 3. Error Correction (Reed-Solomon)
    if use_ecc:
        header.flags |= HeaderFlags.ECC_RS_PRESENT
        rs = RSCodec(nsym=header.rs_n - header.rs_k)

        # Partition into blocks of size k
        blocks = [compressed_payload[i:i+header.rs_k] for i in range(0, len(compressed_payload), header.rs_k)]

        # Encode each block and concatenate
        ecc_payload = b''.join(rs.encode(block) for block in blocks)
    else:
        ecc_payload = compressed_payload

    # 4. Tiling and Pixel Packing
    header_bytes = header.pack()
    tile_w, tile_h = header.tile_w, header.tile_h
    bytes_per_pixel = 4  # RGBA

    # Each tile has a 2x2 fiducial marker, so 16 bytes are reserved
    marker_byte_size = 16 if use_sync_markers else 0
    if use_sync_markers:
        header.flags |= HeaderFlags.SYNC_MARKERS_PRESENT

    # Calculate tile capacity and total number of tiles needed
    tile_data_capacity_bytes = (tile_w * tile_h * bytes_per_pixel) - marker_byte_size
    num_tiles = (len(ecc_payload) + tile_data_capacity_bytes - 1) // tile_data_capacity_bytes

    # Determine image grid layout
    # For simplicity, lay out tiles in a long row for now. A squarer layout is better.
    tiles_across = max(1, int(np.ceil(np.sqrt(num_tiles))))
    tiles_down = (num_tiles + tiles_across - 1) // tiles_across

    # Calculate final image dimensions
    header_h = (HEADER_BYTE_SIZE + (tile_w * bytes_per_pixel) - 1) // (tile_w * bytes_per_pixel)
    img_w = tiles_across * tile_w
    img_h = header_h + (tiles_down * tile_h)

    # Create the full pixel array
    pixel_array = np.zeros((img_h, img_w, 4), dtype=np.uint8)

    # Pack header into the top rows
    header_pixels = np.frombuffer(header_bytes.ljust(header_h * img_w * 4, b'\0'), dtype=np.uint8).reshape(header_h, img_w, 4)
    pixel_array[0:header_h, :] = header_pixels

    # Pack payload into tiles
    payload_ptr = 0
    for i in range(num_tiles):
        tile_y = header_h + (i // tiles_across) * tile_h
        tile_x = (i % tiles_across) * tile_w

        # --- Final, Clean Tiling Logic ---

        # 1. Extract the payload chunk for the current tile.
        payload_chunk = ecc_payload[payload_ptr : payload_ptr + tile_data_capacity_bytes]
        payload_ptr += len(payload_chunk)

        # 2. Create the full tile data buffer, padding as needed.
        # This buffer represents the entire data area of the tile.
        tile_data_bytes = payload_chunk.ljust(tile_data_capacity_bytes, b'\x00')

        # 3. Create the tile pixel array from the data.
        # The marker will be stamped on top of this.
        if use_sync_markers:
            # We construct the full tile bytestream by inserting the marker
            # and then the data. The decoder knows to skip the marker area.

            # We need to construct the full WxH tile.
            # The data that gets overwritten by the marker is irrelevant.
            # So, create the full tile from data, then stamp.

            # The total tile size in bytes.
            total_tile_bytes = tile_w * tile_h * 4

            # The data stream for the entire tile, as if no marker exists.
            # The payload chunk is the size of the data area, so we pad it
            # to fill the whole tile.

            # This is incorrect. The payload chunk is the *data*. The marker
            # replaces some of those bytes.
            # A tile is made of: [marker] + [data]
            # No, a tile is a grid of pixels. The marker is a 2x2 grid of pixels.
            # The data fills the rest.

            # Let's use the simplest possible logic.
            # Create a tile array, fill it with data, then stamp the marker.

            # The total data for a tile (payload + padding)
            full_tile_data_bytes = payload_chunk.ljust(tile_w * tile_h * 4, b'\0')

            # Create a writable copy of the array from the buffer
            tile_pixel_array = np.frombuffer(full_tile_data_bytes, dtype=np.uint8).reshape(tile_h, tile_w, 4).copy()

            # Stamp the fiducial marker on top.
            tile_pixel_array[0:2, 0:2] = FIDUCIAL_MARKER_PIXELS
        else:
            # No marker, just create the tile from the data.
            full_tile_data_bytes = payload_chunk.ljust(tile_w * tile_h * 4, b'\0')
            tile_pixel_array = np.frombuffer(full_tile_data_bytes, dtype=np.uint8).reshape(tile_h, tile_w, 4)

        # 4. Place the finished tile into the main image array
        pixel_array[tile_y:tile_y+tile_h, tile_x:tile_x+tile_w] = tile_pixel_array


    # 5. PNG Creation and Metadata
    img = Image.fromarray(pixel_array, 'RGBA')

    # Add iTXt chunks
    png_info = PngImagePlugin.PngInfo()

    index_data = {
        "ptx": "1.1",
        "encoding": "cbor+zlib" if use_cbor else "utf8+zlib",
        "payload_len": header.payload_len,
        "tile": {"w": header.tile_w, "h": header.tile_h, "rs_k": header.rs_k, "rs_n": header.rs_n},
    }
    png_info.add_text("ptx.index", json.dumps(index_data), zip=False)
    png_info.add_text("ptx.stub", f"PixelText v1.1 | {len(payload)} bytes", zip=False)

    if output_path:
        img.save(output_path, pnginfo=png_info)

    return img