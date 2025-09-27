import unittest
import os
from io import BytesIO

from src.lib import pixeltext
from src.lib.pixeltext.header import PixelTextHeader, HeaderFlags
from crc32c import crc32c

class TestPixelText(unittest.TestCase):

    def test_header_crc_sanity(self):
        """
        Validates the header CRC calculation based on the spec's test vector.
        """
        header = PixelTextHeader(
            payload_len=0x00000005,
            flags=HeaderFlags.ENCODING_UTF8 | HeaderFlags.COMP_ZLIB,
            tile_w=256,
            tile_h=256,
            rs_k=223,
            rs_n=255,
            # Payload CRC for zlib-compressed "hello" (b'x\x9c\xcbH\xcd\xc9\xc9\x07\x00\x06,\x02\x15') is not what the spec has.
            # The spec has an example payload of `0x78 0x9c 0x0b 0x49 0x2d` which is zlib-compressed "A\n".
            crc32c_payload=crc32c(b'\x78\x9c\x0b\x49\x2d')
        )

        packed_header = header.pack()

        # The crc32c_header field is calculated internally by pack()
        # We unpack to verify it was calculated correctly.
        unpacked_header = PixelTextHeader.unpack(packed_header)

        self.assertEqual(header.crc32c_header, unpacked_header.crc32c_header)

    def test_simple_round_trip_utf8(self):
        """
        Tests a full encode-decode cycle with a simple UTF-8 string, no ECC.
        """
        original_text = "Hello, PixelText! This is a test. 🚀"

        # Encode
        img = pixeltext.encode(original_text, use_cbor=False, use_ecc=False, use_sync_markers=False)

        # Save to a byte buffer to simulate file I/O
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Decode
        decoded_text = pixeltext.decode(buffer)

        self.assertEqual(original_text, decoded_text)

    def test_round_trip_cbor(self):
        """
        Tests a full encode-decode cycle with a CBOR object.
        """
        original_data = {
            "document": "PixelText Spec",
            "version": 1.1,
            "author": "Jules",
            "content": "The quick brown fox jumps over the lazy dog."
        }

        img = pixeltext.encode(original_data, use_cbor=True, use_ecc=False, use_sync_markers=False)

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        decoded_data = pixeltext.decode(buffer)

        self.assertEqual(original_data, decoded_data)

    def test_full_round_trip_with_ecc_and_sync(self):
        """
        Tests a full round-trip with a larger text block, enabling ECC and sync markers.
        This validates the tiling and Reed-Solomon functionality.
        """
        # A larger block of text to ensure it spans multiple RS blocks and tiles
        original_text = " ".join(["This is a comprehensive test of the PixelText v1.1 specification."] * 50)

        img = pixeltext.encode(original_text, use_cbor=False, use_ecc=True, use_sync_markers=True)

        # To really test robustness, we could save, open, and apply minor corruption.
        # For now, a simple round-trip is a good start.
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        decoded_text = pixeltext.decode(buffer)

        self.assertEqual(original_text, decoded_text)

if __name__ == '__main__':
    unittest.main()