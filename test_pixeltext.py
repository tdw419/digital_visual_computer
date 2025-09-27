import os
import unittest
from encoder import encode_to_image
from decoder import decode_from_image

class TestPixelTextV0(unittest.TestCase):

    def setUp(self):
        """Set up for the tests."""
        self.test_file = "test_image.png"
        # Clean up any old test files before running a new test
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def tearDown(self):
        """Tear down after the tests."""
        # Clean up the created test file
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_round_trip_basic_ascii(self):
        """Test encoding and decoding with simple ASCII text."""
        original_text = "Hello, World!"
        encode_to_image(original_text, self.test_file)
        decoded_text = decode_from_image(self.test_file)
        self.assertEqual(original_text, decoded_text)

    def test_round_trip_with_unicode(self):
        """Test encoding and decoding with a mix of ASCII and Unicode."""
        original_text = "Testing Unicode: 你好, 🌍, and 🚀"
        encode_to_image(original_text, self.test_file)
        decoded_text = decode_from_image(self.test_file)
        self.assertEqual(original_text, decoded_text)

    def test_round_trip_empty_string(self):
        """Test encoding and decoding an empty string."""
        original_text = ""
        encode_to_image(original_text, self.test_file)
        decoded_text = decode_from_image(self.test_file)
        self.assertEqual(original_text, decoded_text)

    def test_round_trip_long_string(self):
        """Test with a longer string that forces image to be non-trivial size."""
        original_text = "This is a much longer string designed to test the image resizing and pixel padding logic. It needs to be sufficiently long to ensure that the width calculation and height calculation are exercised properly." * 5
        encode_to_image(original_text, self.test_file)
        decoded_text = decode_from_image(self.test_file)
        self.assertEqual(original_text, decoded_text)

if __name__ == '__main__':
    unittest.main()