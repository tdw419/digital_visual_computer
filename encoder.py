import math
from PIL import Image

def encode_to_image(text: str, output_path: str):
    """
    Encodes a text string into a PNG image using the PixelText v0 format.
    - 1 character per pixel.
    - Header row stores metadata.
    """
    magic = "PTX1"

    # --- Prepare Header ---
    # We'll use pixels for the header. Let's define a simple header format.
    # Pixel 0: Magic string (encoded as text)
    # Pixel 1: Text length (as a number)
    # For simplicity, we'll encode the magic string itself as pixels.
    header_pixels = []
    for char in magic:
        codepoint = ord(char)
        r = (codepoint >> 16) & 0xFF
        g = (codepoint >> 8) & 0xFF
        b = codepoint & 0xFF
        header_pixels.append((r, g, b))

    # Encode the length of the text as a single pixel.
    # This supports text length up to 2^24-1, which is plenty.
    text_len = len(text)
    len_r = (text_len >> 16) & 0xFF
    len_g = (text_len >> 8) & 0xFF
    len_b = text_len & 0xFF
    header_pixels.append((len_r, len_g, len_b))

    # --- Prepare Content ---
    content_pixels = []
    for char in text:
        codepoint = ord(char)
        r = (codepoint >> 16) & 0xFF
        g = (codepoint >> 8) & 0xFF
        b = codepoint & 0xFF
        content_pixels.append((r, g, b))

    # --- Create Image ---
    all_pixels = header_pixels + content_pixels
    total_pixels = len(all_pixels)

    # Calculate image dimensions (as close to a square as possible)
    width = int(math.sqrt(total_pixels)) + 1
    height = math.ceil(total_pixels / width)

    # Create the image
    img = Image.new('RGB', (width, height), color='black')

    # Add padding with U+0000 (black pixels) to fill the image
    padding_needed = (width * height) - total_pixels
    all_pixels.extend([(0, 0, 0)] * padding_needed)

    # Put data into the image
    img.putdata(all_pixels)

    # Save the image
    img.save(output_path, 'PNG')
    print(f"Successfully encoded text into {output_path}")

if __name__ == '__main__':
    sample_text = "Hello, PixelText! This is a test. 🚀"
    output_file = "output_v0.png"
    encode_to_image(sample_text, output_file)