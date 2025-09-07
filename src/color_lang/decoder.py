import os
from PIL import Image
from color_lang.exceptions import PaletteError

class PngDecoder:
    def __init__(self, palette):
        self.palette = palette

    def load_png_deterministically(self, file_path: str):
        """Loads a PNG file deterministically."""
        # TODO: Implement deterministic loading (e.g., sorting pixels, consistent color space)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PNG file not found: {file_path}")
        
        image = Image.open(file_path).convert("RGB")
        return image

    def extract_tiles_and_sample_centers(self, image: Image.Image, tile_size: int = 16):
        """Extracts 16x16 tiles and samples their center pixels."""
        tiles = []
        width, height = image.size
        
        grid_width = width // tile_size
        grid_height = height // tile_size

        for y in range(0, height, tile_size):
            for x in range(0, width, tile_size):
                # Ensure we don't go out of bounds for the last tile
                right = min(x + tile_size, width)
                bottom = min(y + tile_size, height)
                
                tile = image.crop((x, y, right, bottom))
                
                # Sample center pixel
                center_x = tile.width // 2
                center_y = tile.height // 2
                center_pixel = tile.getpixel((center_x, center_y))
                
                tiles.append({"tile": tile, "center_pixel": center_pixel, "x": x, "y": y})
        return tiles, grid_width, grid_height

    def match_colors_to_opcodes(self, pixel_data):
        """Matches colors to palette opcodes with tolerance."""
        try:
            opcode, _ = self.palette.match_color(list(pixel_data)) # Convert tuple to list for match_color
            return opcode
        except PaletteError:
            return None # No matching color found

    def decode_png(self, file_path: str):
        """Main method to decode a PNG into DVC opcodes."""
        image = self.load_png_deterministically(file_path)
        tiles_data, grid_width, grid_height = self.extract_tiles_and_sample_centers(image, tile_size=self.palette.tile_size)
        
        decoded_opcodes = []
        for tile_info in tiles_data:
            opcode = self.match_colors_to_opcodes(tile_info["center_pixel"])
            decoded_opcodes.append(opcode)
        
        return decoded_opcodes, grid_width, grid_height