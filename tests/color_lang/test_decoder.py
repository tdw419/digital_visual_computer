import pytest
from pathlib import Path
import json
from PIL import Image

from src.color_lang.palette import ColorPalette
from src.color_lang.decoder import PngDecoder
from src.color_lang.lower import ColorLowerer
from src.color_lang.compiler import ColorCompiler

@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def simple_2x2_palette(fixtures_dir):
    return ColorPalette.from_file(fixtures_dir / "simple_2x2_palette.json")

@pytest.fixture
def simple_2x2_png_path(fixtures_dir):
    return fixtures_dir / "simple_2x2.png"

class TestPngDecodingAndLowering:
    def test_decode_2x2_png_to_opcodes(self, simple_2x2_palette, simple_2x2_png_path):
        decoder = PngDecoder(simple_2x2_palette)
        decoded_opcodes, grid_width, grid_height = decoder.decode_png(str(simple_2x2_png_path))

        expected_opcodes = ["RED_OP", "GREEN_OP", "BLUE_OP", "WHITE_OP"]
        assert decoded_opcodes == expected_opcodes
        assert grid_width == 2
        assert grid_height == 2

    def test_lower_2x2_opcodes_to_dvc_ir(self, simple_2x2_palette, simple_2x2_png_path):
        decoder = PngDecoder(simple_2x2_palette)
        decoded_opcodes, _, _ = decoder.decode_png(str(simple_2x2_png_path))

        lowerer = ColorLowerer()
        dvc_ir = lowerer.lower_to_dvc_ir(decoded_opcodes)

        assert "metadata" in dvc_ir
        assert "program" in dvc_ir
        assert len(dvc_ir["program"]) == 4
        assert dvc_ir["program"][0]["opcode"] == "RED_OP"
        assert dvc_ir["program"][1]["opcode"] == "GREEN_OP"
        assert dvc_ir["program"][2]["opcode"] == "BLUE_OP"
        assert dvc_ir["program"][3]["opcode"] == "WHITE_OP"
        assert dvc_ir["metadata"]["unrecognized_colors"] == 0

    def test_color_compiler_e2e(self, simple_2x2_palette, simple_2x2_png_path):
        compiler = ColorCompiler(simple_2x2_palette)
        dvc_ir, summary = compiler.compile_and_summarize(str(simple_2x2_png_path))

        assert "metadata" in dvc_ir
        assert "program" in dvc_ir
        assert len(dvc_ir["program"]) == 4
        assert dvc_ir["metadata"]["grid_size"] == {"width": 2, "height": 2}
        assert dvc_ir["metadata"]["unrecognized_colors"] == 0
        assert "ColorCompiler-v0.1" in dvc_ir["metadata"]["compiler"]
        assert "Compilation Summary" in summary
        assert "Total Instructions: 4" in summary
        assert "Grid Size: 2x2" in summary
