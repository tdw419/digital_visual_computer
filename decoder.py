from PIL import Image

def decode_from_image(image_path: str) -> str:
    """
    Decodes a text string from a PNG image encoded in the PixelText v0 format.
    """
    try:
        img = Image.open(image_path)
    except FileNotFoundError:
        return "Error: Image file not found."

    # Load all pixels from the image
    pixels = list(img.getdata())

    # --- Decode Header ---
    # The first 4 pixels should be the magic string "PTX1"
    magic_len = 4
    expected_magic = "PTX1"

    if len(pixels) < magic_len + 1:
        return "Error: Image is too small to contain a valid header."

    decoded_magic = ""
    for i in range(magic_len):
        r, g, b = pixels[i]
        codepoint = (r << 16) | (g << 8) | b
        decoded_magic += chr(codepoint)

    if decoded_magic != expected_magic:
        return f"Error: Invalid magic string. Expected {expected_magic}, got {decoded_magic}."

    # The 5th pixel contains the length of the text
    len_r, len_g, len_b = pixels[magic_len]
    text_len = (len_r << 16) | (len_g << 8) | len_b

    # --- Decode Content ---
    start_of_content = magic_len + 1
    end_of_content = start_of_content + text_len

    if len(pixels) < end_of_content:
        return "Error: Image data is shorter than indicated by the header length."

    decoded_chars = []
    for i in range(start_of_content, end_of_content):
        r, g, b = pixels[i]
        codepoint = (r << 16) | (g << 8) | b
        # U+0000 is used for padding, so we should handle it, although it shouldn't be in the main content
        if codepoint == 0 and i >= start_of_content + text_len:
             continue
        decoded_chars.append(chr(codepoint))

    return "".join(decoded_chars)


if __name__ == '__main__':
    input_file = "output_v0.png"
    decoded_text = decode_from_image(input_file)
    print("Decoded Text:")
    print(decoded_text)

    # For comparison, let's re-create the original text
    original_text = "Hello, PixelText! This is a test. 🚀"
    print("\nOriginal Text:")
    print(original_text)

    # Verification
    if decoded_text == original_text:
        print("\n✅ Verification successful: Decoded text matches original.")
    else:
        print("\n❌ Verification failed: Decoded text does not match original.")