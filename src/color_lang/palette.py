"""
ColorPalette data model for mapping RGB colors to DVC opcodes.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Union

from .exceptions import PaletteError


# Valid DVC opcodes
VALID_OPCODES = {
    "NOP", "HALT", "PUSHI", "POP", "ADD", "SUB", "MUL", "DIV", "PRINT",
    "RED_OP", "GREEN_OP", "BLUE_OP", "WHITE_OP"
}


class ColorPalette:
    """
    Represents a palette mapping RGB colors to DVC opcodes.
    
    Handles color validation, tolerance-based matching, and immediate value encoding.
    """
    
    def __init__(self, 
                 version: str,
                 tile_size: int,
                 opcodes: Dict[str, str],
                 scan_order: str = "row-major",
                 immediate_mode: str = "rgb-to-int", 
                 tolerance: float = 5.0,
                 fiducials: Dict[str, str] = None):
        """Initialize ColorPalette with validated parameters."""
        self.version = version
        self.tile_size = tile_size  
        self.scan_order = scan_order
        self.opcodes = opcodes
        self.immediate_mode = immediate_mode
        self.tolerance = tolerance
        self.fiducials = fiducials or {}

    @classmethod
    def from_dict(cls, data: Dict) -> "ColorPalette":
        """Create ColorPalette from dictionary, validating all fields."""
        # Validate version
        if "version" not in data:
            raise PaletteError("Palette missing required 'version' field")
        if data["version"] != "palette-v0.1":
            raise PaletteError(f"Unsupported palette version: {data['version']}")
            
        # Validate tile_size
        if "tile_size" not in data:
            raise PaletteError("Palette missing required 'tile_size' field")
        tile_size = data["tile_size"]
        if not isinstance(tile_size, int) or tile_size <= 0:
            raise PaletteError(f"Invalid tile_size: must be positive integer, got {tile_size}")
            
        # Validate opcodes
        if "opcodes" not in data:
            raise PaletteError("Palette missing required 'opcodes' field")
        opcodes = data["opcodes"]
        if not opcodes:
            raise PaletteError("Palette opcodes cannot be empty")
            
        # Validate opcode format and names
        for color_hex, opcode in opcodes.items():
            # Validate hex color format
            if not isinstance(color_hex, str) or len(color_hex) != 6:
                raise PaletteError(f"Invalid hex color format: '{color_hex}' (must be 6-character RRGGBB)")
            try:
                int(color_hex, 16)  # Test if valid hex
            except ValueError:
                raise PaletteError(f"Invalid hex color format: '{color_hex}' (must be valid hexadecimal)")
                
            # Validate opcode name
            if opcode not in VALID_OPCODES:
                raise PaletteError(f"Invalid opcode: '{opcode}' (valid: {sorted(VALID_OPCODES)})")
        
        # Get optional fields with defaults
        scan_order = data.get("scan_order", "row-major")
        immediate_mode = data.get("immediate_mode", "rgb-to-int")
        tolerance = data.get("tolerance", 5.0)
        fiducials = data.get("fiducials", {})
        
        return cls(
            version=data["version"],
            tile_size=tile_size,
            opcodes=opcodes,
            scan_order=scan_order,
            immediate_mode=immediate_mode,
            tolerance=tolerance,
            fiducials=fiducials
        )

    @classmethod 
    def from_file(cls, path: Union[str, Path]) -> "ColorPalette":
        """Load ColorPalette from JSON file."""
        path = Path(path)
        if not path.exists():
            raise PaletteError(f"Palette file not found: {path}")
            
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PaletteError(f"Invalid JSON in palette file: {e}")
        except Exception as e:
            raise PaletteError(f"Error reading palette file: {e}")
            
        return cls.from_dict(data)

    def match_color(self, rgb: List[int]) -> Tuple[str, str]:
        """
        Match RGB color to palette entry within tolerance.
        
        Args:
            rgb: [R, G, B] color components (0-255)
            
        Returns:
            (opcode, hex_color) tuple for matching palette entry
            
        Raises:
            PaletteError: If no palette entry matches within tolerance
        """
        rgb_hex = self.rgb_to_hex(rgb)
        
        # Try exact match first
        if rgb_hex in self.opcodes:
            return (self.opcodes[rgb_hex], rgb_hex)
            
        # Try tolerance-based matching
        if self.tolerance > 0:
            best_match = None
            best_distance = float('inf')
            
            for palette_hex, opcode in self.opcodes.items():
                palette_rgb = self.hex_to_rgb(palette_hex)
                distance = self._color_distance(rgb, palette_rgb)
                
                if distance <= self.tolerance and distance < best_distance:
                    best_distance = distance
                    best_match = (opcode, palette_hex)
                    
            if best_match:
                return best_match
        
        # No match found
        raise PaletteError(f"No matching color for RGB{rgb} within tolerance {self.tolerance}")

    def encode_immediate(self, rgb: List[int]) -> int:
        """
        Encode RGB color as immediate integer value.
        
        Uses formula: r + (g << 8) + (b << 16)
        """
        r, g, b = rgb
        return r + (g << 8) + (b << 16)

    def is_fiducial(self, rgb: List[int]) -> bool:
        """Check if RGB color is a fiducial (reserved) color."""
        rgb_hex = self.rgb_to_hex(rgb)
        return rgb_hex in self.fiducials

    def get_fiducial(self, rgb: List[int]) -> str:
        """Get fiducial type for RGB color."""
        rgb_hex = self.rgb_to_hex(rgb)
        return self.fiducials.get(rgb_hex)

    @staticmethod
    def rgb_to_hex(rgb: List[int]) -> str:
        """Convert RGB array to hex string."""
        r, g, b = rgb
        return f"{r:02X}{g:02X}{b:02X}"

    @staticmethod 
    def hex_to_rgb(hex_color: str) -> List[int]:
        """Convert hex string to RGB array."""
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)  
        b = int(hex_color[4:6], 16)
        return [r, g, b]

    def _color_distance(self, rgb1: List[int], rgb2: List[int]) -> float:
        """
        Calculate Euclidean color distance in RGB space.
        
        For v0.1, using simple RGB distance. Future versions may use 
        perceptual color spaces like CIELAB.
        """
        r1, g1, b1 = rgb1
        r2, g2, b2 = rgb2
        return math.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2)