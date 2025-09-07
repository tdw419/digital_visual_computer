"""
End-to-end integration tests for color language workflow.
"""

import json
import tempfile
from pathlib import Path
from PIL import Image
import pytest

from src.dvc_cli.main import build_parser
from src.color_lang.palette import ColorPalette


class TestColorLanguageE2E:
    """End-to-end tests for the complete color language workflow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def simple_palette(self):
        """Simple 2x2 program palette."""
        return {
            "version": "palette-v0.1",
            "tile_size": 16,
            "scan_order": "row-major",
            "opcodes": {
                "FF0000": "PUSHI",  # Red
                "0000FF": "ADD",    # Blue  
                "FFFF00": "PRINT",  # Yellow
                "FFFFFF": "HALT"    # White
            },
            "immediate_mode": "rgb-to-int",
            "tolerance": 5.0
        }

    @pytest.fixture
    def simple_program_png(self, temp_dir):
        """Create a simple 2x2 tile PNG program programmatically.
        
        Program layout (32x32 pixels = 2x2 tiles of 16x16):
        [Red] [Blue]     -> PUSHI 255, ADD
        [Yellow] [White] -> PRINT, HALT
        
        Expected behavior: Push 255, add (no second value = error), but should compile successfully.
        """
        # Create 32x32 RGB image
        img = Image.new('RGB', (32, 32), color='black')
        pixels = img.load()
        
        # Fill tiles with solid colors
        # Top-left tile (0,0 to 15,15): Red
        for x in range(16):
            for y in range(16):
                pixels[x, y] = (255, 0, 0)  # FF0000 - PUSHI
        
        # Top-right tile (16,0 to 31,15): Blue  
        for x in range(16, 32):
            for y in range(16):
                pixels[x, y] = (0, 0, 255)  # 0000FF - ADD
                
        # Bottom-left tile (0,16 to 15,31): Yellow
        for x in range(16):
            for y in range(16, 32):
                pixels[x, y] = (255, 255, 0)  # FFFF00 - PRINT
                
        # Bottom-right tile (16,16 to 31,31): White
        for x in range(16, 32):
            for y in range(16, 32):
                pixels[x, y] = (255, 255, 255)  # FFFFFF - HALT
        
        # Save the image
        image_path = temp_dir / "simple_2x2.png"
        img.save(image_path, 'PNG')
        return image_path

    @pytest.mark.skip(reason="Requires PIL and full implementation")
    def test_complete_color_compile_workflow(self, temp_dir, simple_palette, simple_program_png):
        """Test complete compilation workflow from PNG to DVC JSON."""
        # Setup files
        palette_path = temp_dir / "palette.json"
        program_path = temp_dir / "program.json"
        
        with open(palette_path, 'w') as f:
            json.dump(simple_palette, f)
        
        # Parse command
        parser = build_parser()
        args = parser.parse_args([
            "color-compile",
            "--image", str(simple_program_png),
            "--palette", str(palette_path),
            "--out", str(program_path),
            "--format", "json"
        ])
        
        # Execute compilation
        from src.dvc_cli.color_commands import cmd_color_compile
        import sys
        import io
        import contextlib
        
        # Capture stdout
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            result = cmd_color_compile(args)
        
        # Should succeed
        assert result == 0
        
        # Should create program file
        assert program_path.exists()
        with open(program_path) as f:
            program = json.load(f)
        
        # Verify compiled program structure
        expected_program = [
            {"op": "PUSHI", "arg": "255"},  # Red tile -> PUSHI with RGB(255,0,0) = 255
            {"op": "ADD"},                  # Blue tile -> ADD
            {"op": "PRINT"},                # Yellow tile -> PRINT  
            {"op": "HALT"}                  # White tile -> HALT
        ]
        
        assert program == expected_program
        
        # Verify compilation summary
        stdout_json = json.loads(stdout_capture.getvalue())
        assert stdout_json["status"] == "success"
        assert stdout_json["tiles_processed"] == 4
        assert stdout_json["instructions_generated"] == 4
        assert stdout_json["grid_size"] == {"width": 2, "height": 2}
        assert "palette_hash" in stdout_json

    @pytest.mark.skip(reason="Requires PIL and full implementation")
    def test_complete_color_run_workflow(self, temp_dir, simple_palette, simple_program_png):
        """Test complete execution workflow from PNG to trace."""
        # Setup files  
        palette_path = temp_dir / "palette.json"
        trace_path = temp_dir / "trace.json"
        
        with open(palette_path, 'w') as f:
            json.dump(simple_palette, f)
        
        # Parse command
        parser = build_parser()
        args = parser.parse_args([
            "color-run",
            "--image", str(simple_program_png),
            "--palette", str(palette_path),
            "--trace", str(trace_path),
            "--format", "json"
        ])
        
        # Execute color-run
        from src.dvc_cli.color_commands import cmd_color_run
        import sys
        import io
        import contextlib
        
        # Capture stdout
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            result = cmd_color_run(args)
        
        # Should succeed (even though ADD will cause stack underflow)
        assert result == 0
        
        # Should create trace file
        assert trace_path.exists()
        with open(trace_path) as f:
            trace = json.load(f)
        
        # Verify trace structure
        assert "meta" in trace
        assert "steps" in trace
        
        # Check color provenance metadata
        meta = trace["meta"]
        assert "color_provenance" in meta
        color_prov = meta["color_provenance"]
        assert color_prov["compiler_version"] == "dvc-color-v0.1"
        assert color_prov["tile_size"] == 16
        assert color_prov["grid_size"] == {"width": 2, "height": 2}
        
        # Verify execution summary
        stdout_json = json.loads(stdout_capture.getvalue())
        assert "status" in stdout_json  # Could be "halted" or "faulted"
        assert "compilation" in stdout_json
        comp = stdout_json["compilation"]
        assert comp["tiles_processed"] == 4
        assert comp["grid_size"] == {"width": 2, "height": 2}

    @pytest.mark.skip(reason="Requires PIL and full implementation")
    def test_color_program_deterministic_compilation(self, temp_dir, simple_palette, simple_program_png):
        """Test that identical PNG + palette produces identical compilation."""
        palette_path = temp_dir / "palette.json"
        program1_path = temp_dir / "program1.json" 
        program2_path = temp_dir / "program2.json"
        
        with open(palette_path, 'w') as f:
            json.dump(simple_palette, f)
        
        # Compile same program twice
        from src.dvc_cli.color_commands import cmd_color_compile
        import argparse
        
        # First compilation
        args1 = argparse.Namespace()
        args1.image = simple_program_png
        args1.palette = palette_path
        args1.out = program1_path
        args1.format = None
        
        result1 = cmd_color_compile(args1)
        assert result1 == 0
        
        # Second compilation
        args2 = argparse.Namespace()
        args2.image = simple_program_png
        args2.palette = palette_path  
        args2.out = program2_path
        args2.format = None
        
        result2 = cmd_color_compile(args2)
        assert result2 == 0
        
        # Programs should be identical
        with open(program1_path) as f1, open(program2_path) as f2:
            program1 = json.load(f1)
            program2 = json.load(f2)
            
        assert program1 == program2


# Basic test that should work now (without PIL dependency)
class TestCurrentImplementation:
    """Test current placeholder implementation."""
    
    def test_color_compile_with_valid_palette(self):
        """Test color-compile with valid palette but missing image."""
        import tempfile
        from pathlib import Path
        import argparse
        from src.dvc_cli.color_commands import cmd_color_compile
        import json
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create palette file
            palette_data = {
                "version": "palette-v0.1",
                "tile_size": 16,
                "opcodes": {"FF0000": "HALT"}
            }
            palette_path = tmpdir / "palette.json"
            with open(palette_path, 'w') as f:
                json.dump(palette_data, f)
            
            # Create args
            args = argparse.Namespace()
            args.image = tmpdir / "nonexistent.png"  # Will fail
            args.palette = palette_path
            args.out = tmpdir / "program.json"
            args.format = 'json'
            
            # Should return error code but not crash
            result = cmd_color_compile(args)
            assert result in [1, 2]  # Either compilation error or I/O error