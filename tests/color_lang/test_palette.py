"""
Unit tests for ColorPalette data model and validation.
"""

import json
import pytest
from pathlib import Path

# These imports will fail initially - that's expected for TDD
try:
    from src.color_lang.palette import ColorPalette, PaletteError
except ImportError:
    # Mark as expected failures until implementation exists
    ColorPalette = None
    PaletteError = Exception


class TestColorPalette:
    """Test ColorPalette loading, validation, and color matching."""

    @pytest.fixture
    def valid_palette_data(self):
        """Valid palette JSON for testing."""
        return {
            "version": "palette-v0.1",
            "tile_size": 16,
            "scan_order": "row-major",
            "opcodes": {
                "FF0000": "PUSHI",
                "00FF00": "POP", 
                "0000FF": "ADD",
                "FFFFFF": "HALT"
            },
            "immediate_mode": "rgb-to-int",
            "tolerance": 5.0
        }

    @pytest.fixture
    def fixtures_dir(self):
        """Path to test fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_load_valid_palette(self, valid_palette_data):
        """Test loading a valid palette from JSON data."""
        palette = ColorPalette.from_dict(valid_palette_data)
        
        assert palette.version == "palette-v0.1"
        assert palette.tile_size == 16
        assert palette.scan_order == "row-major"
        assert palette.tolerance == 5.0
        assert len(palette.opcodes) == 4
        assert palette.opcodes["FF0000"] == "PUSHI"

    def test_load_palette_from_file(self, fixtures_dir):
        """Test loading palette from JSON file."""
        palette_path = fixtures_dir / "simple_2x2_palette.json"
        palette = ColorPalette.from_file(palette_path)
        
        assert palette.version == "palette-v0.1"
        assert "FF0000" in palette.opcodes
        assert palette.opcodes["FF0000"] == "RED_OP"

    def test_validate_schema_version(self):
        """Test palette version validation."""
        # Missing version
        with pytest.raises(PaletteError, match="version"):
            ColorPalette.from_dict({"tile_size": 16, "opcodes": {}})
            
        # Invalid version
        with pytest.raises(PaletteError, match="version"):
            ColorPalette.from_dict({"version": "invalid", "tile_size": 16, "opcodes": {}})

    def test_validate_tile_size(self):
        """Test tile size validation."""
        base_data = {"version": "palette-v0.1", "opcodes": {"FF0000": "HALT"}}
        
        # Missing tile_size
        with pytest.raises(PaletteError, match="tile_size"):
            ColorPalette.from_dict(base_data)
            
        # Invalid tile_size (not positive integer)
        with pytest.raises(PaletteError, match="tile_size"):
            ColorPalette.from_dict({**base_data, "tile_size": 0})
            
        with pytest.raises(PaletteError, match="tile_size"):
            ColorPalette.from_dict({**base_data, "tile_size": -1})

    def test_validate_opcodes(self):
        """Test opcode mapping validation.""" 
        base_data = {"version": "palette-v0.1", "tile_size": 16}
        
        # Missing opcodes
        with pytest.raises(PaletteError, match="opcodes"):
            ColorPalette.from_dict(base_data)
            
        # Empty opcodes
        with pytest.raises(PaletteError, match="opcodes"):
            ColorPalette.from_dict({**base_data, "opcodes": {}})
            
        # Invalid hex color format
        with pytest.raises(PaletteError, match="color.*format"):
            ColorPalette.from_dict({**base_data, "opcodes": {"invalid": "HALT"}})
            
        # Invalid opcode name
        with pytest.raises(PaletteError, match="opcode.*INVALID"):
            ColorPalette.from_dict({**base_data, "opcodes": {"FF0000": "INVALID_OP"}})

    def test_color_matching_exact(self, valid_palette_data):
        """Test exact RGB color matching."""
        palette = ColorPalette.from_dict(valid_palette_data)
        
        # Exact matches
        assert palette.match_color([255, 0, 0]) == ("PUSHI", "FF0000")
        assert palette.match_color([0, 255, 0]) == ("POP", "00FF00")
        assert palette.match_color([0, 0, 255]) == ("ADD", "0000FF")
        assert palette.match_color([255, 255, 255]) == ("HALT", "FFFFFF")

    def test_color_matching_tolerance(self, valid_palette_data):
        """Test color matching with tolerance."""
        palette = ColorPalette.from_dict(valid_palette_data)
        
        # Colors within tolerance (default 5.0 RGB distance)
        assert palette.match_color([252, 2, 2]) == ("PUSHI", "FF0000")  # Distance ~4.6 from red
        assert palette.match_color([2, 252, 2]) == ("POP", "00FF00")    # Distance ~4.6 from green
        
    def test_color_matching_no_match(self, valid_palette_data):
        """Test color matching when no palette entry matches."""
        palette = ColorPalette.from_dict(valid_palette_data)
        
        # Color too far from any palette entry
        with pytest.raises(PaletteError, match="No matching color"):
            palette.match_color([128, 128, 128])  # Gray, not close to any palette color

    def test_immediate_value_encoding(self, valid_palette_data):
        """Test RGB to integer immediate value conversion."""
        palette = ColorPalette.from_dict(valid_palette_data)
        
        # Test RGB to integer conversion: r + (g << 8) + (b << 16)
        assert palette.encode_immediate([255, 0, 0]) == 255        # Red
        assert palette.encode_immediate([0, 255, 0]) == 65280      # Green  
        assert palette.encode_immediate([0, 0, 255]) == 16711680   # Blue
        assert palette.encode_immediate([255, 255, 255]) == 16777215  # White
        assert palette.encode_immediate([42, 0, 0]) == 42          # Arbitrary value

    def test_hex_color_conversion(self):
        """Test RGB array to hex string conversion."""
        # This will be a utility method on ColorPalette
        assert ColorPalette.rgb_to_hex([255, 0, 0]) == "FF0000"
        assert ColorPalette.rgb_to_hex([0, 255, 0]) == "00FF00"
        assert ColorPalette.rgb_to_hex([0, 0, 255]) == "0000FF"
        assert ColorPalette.rgb_to_hex([255, 255, 255]) == "FFFFFF"
        assert ColorPalette.rgb_to_hex([0, 0, 0]) == "000000"

    def test_fiducials_handling(self):
        """Test fiducial color handling (reserved colors)."""
        palette_data = {
            "version": "palette-v0.1",
            "tile_size": 16,
            "opcodes": {"FF0000": "HALT"},
            "fiducials": {
                "808080": "ALIGN",
                "404040": "VERSION"
            }
        }
        
        palette = ColorPalette.from_dict(palette_data)
        
        # Fiducials should be recognized but handled specially
        assert palette.is_fiducial([128, 128, 128])  # Gray
        assert palette.get_fiducial([128, 128, 128]) == "ALIGN"
        assert not palette.is_fiducial([255, 0, 0])  # Red (regular opcode)


class TestPaletteValidationEdgeCases:
    """Test edge cases and error conditions for palette validation."""

    def test_malformed_json_file(self, tmp_path):
        """Test handling of malformed JSON palette files."""
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text("{ invalid json")
        
        with pytest.raises(PaletteError, match="JSON"):
            ColorPalette.from_file(malformed_file)

    def test_missing_palette_file(self, tmp_path):
        """Test handling of missing palette files."""
        missing_file = tmp_path / "missing.json"
        
        with pytest.raises(PaletteError, match="file not found"):
            ColorPalette.from_file(missing_file)

    def test_large_tile_size(self):
        """Test very large tile sizes."""
        palette_data = {
            "version": "palette-v0.1",
            "tile_size": 1024,  # Large but valid
            "opcodes": {"FF0000": "HALT"}
        }
        
        palette = ColorPalette.from_dict(palette_data)
        assert palette.tile_size == 1024

    def test_zero_tolerance(self):
        """Test zero tolerance (exact matching only)."""
        palette_data = {
            "version": "palette-v0.1", 
            "tile_size": 16,
            "opcodes": {"FF0000": "HALT"},
            "tolerance": 0.0
        }
        
        palette = ColorPalette.from_dict(palette_data)
        
        # Exact match should work
        assert palette.match_color([255, 0, 0]) == ("HALT", "FF0000")
        
        # Close color should fail with zero tolerance
        with pytest.raises(PaletteError):
            palette.match_color([254, 0, 0])