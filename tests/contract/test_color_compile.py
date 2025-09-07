"""
Contract tests for dvc color-compile command.
Tests the CLI interface matches the specification in contracts/color-compile.md
"""

import json
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from src.dvc_cli.main import build_parser
from src.dvc_cli.color_commands import cmd_color_compile

import io
from contextlib import redirect_stdout


class TestColorCompileContract:
    """Test color-compile CLI contract compliance."""

    def test_color_compile_command_exists(self):
        """Test that color-compile command is properly registered (GREEN phase)."""
        parser = build_parser()
        
        # Should parse successfully now that command exists
        try:
            args = parser.parse_args([
                "color-compile", 
                "--image", "test.png",
                "--palette", "test.json", 
                "--out", "test.json"
            ])
            assert args.command == "color-compile"
            assert args.image == "test.png"
            assert args.palette == "test.json"
            assert args.out == "test.json"
        except SystemExit:
            pytest.fail("color-compile command should parse successfully")

    # @pytest.mark.skip(reason="Will implement in GREEN phase")
    def test_color_compile_success_contract(self):
        """Test successful compilation returns expected JSON format.
        
        This test defines the contract but will be skipped until implementation.
        """
        # Contract requirements from color-compile.md:
        # 1. Inputs: --image <program.png> --palette <palette.json> --out <program.json>
        # 2. Outputs: DVC JSON program file + compilation summary to stdout
        # 3. Exit codes: 0 (success), 1 (compilation error), 2 (I/O error)
        # 4. Stdout format: {"status": "success", "tiles_processed": N, ...}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create dummy PNG image (16x16 red square)
            image_path = tmp_path / "program.png"
            img = Image.new('RGB', (16, 16), color = 'red')
            img.save(image_path)

            # Create dummy palette.json
            palette_path = tmp_path / "palette.json"
            palette_data = {
                "version": "palette-v0.1",
                "tile_size": 16,
                "opcodes": {
                    "FF0000": "PUSHI"
                },
                "immediate_mode": "rgb-to-int",
                "tolerance": 5.0
            }
            with open(palette_path, 'w') as f:
                json.dump(palette_data, f)

            # Define output path
            output_program_path = tmp_path / "program.json"

            # Prepare args for cmd_color_compile
            parser = build_parser()
            args = parser.parse_args([
                "color-compile",
                "--image", str(image_path),
                "--palette", str(palette_path),
                "--out", str(output_program_path),
                "--format", "json" # Request JSON output for easier parsing
            ])

            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cmd_color_compile(args)
            stdout_output = f.getvalue()

            # Assert exit code
            assert exit_code == 0

            # Assert output program file content
            assert output_program_path.exists()
            with open(output_program_path, 'r') as f:
                program_content = json.load(f)
            assert program_content == [{"opcode": "PUSHI"}]

            # Assert stdout summary content
            summary = json.loads(stdout_output)
            assert summary["status"] == "success"
            assert summary["tiles_processed"] == 1
            assert summary["instructions_generated"] == 1
            assert summary["program_path"] == str(output_program_path)
            assert summary["grid_size"] == {"width": 1, "height": 1}
            assert summary["unrecognized_colors"] == 0
            assert "palette_hash" in summary # Check for presence, actual hash depends on content

    # @pytest.mark.skip(reason="Will implement in GREEN phase") 
    def test_color_compile_error_handling(self):
        """Test error cases and exit codes match contract.
        
        This test defines error handling contract but will be skipped until implementation.
        """
        # Contract requirements:
        # - Exit 1 for compilation errors (unrecognized colors, malformed palette)  
        # - Exit 2 for I/O errors (missing files, write permissions)
        # - Error JSON format: {"status": "error", "error": "description", ...}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parser = build_parser()

            # --- Test Case 1: Missing image file ---
            non_existent_image_path = tmp_path / "non_existent.png"
            palette_path = tmp_path / "palette.json"
            output_program_path = tmp_path / "program.json"

            # Create a valid palette for this test
            palette_data = {
                "version": "palette-v0.1",
                "tile_size": 16,
                "opcodes": {"FF0000": "PUSHI"},
                "immediate_mode": "rgb-to-int",
                "tolerance": 5.0
            }
            with open(palette_path, 'w') as f:
                json.dump(palette_data, f)

            args = parser.parse_args([
                "color-compile",
                "--image", str(non_existent_image_path),
                "--palette", str(palette_path),
                "--out", str(output_program_path),
                "--format", "json"
            ])
            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cmd_color_compile(args)
            stdout_output = f.getvalue()
            assert exit_code == 2
            summary = json.loads(stdout_output)
            assert summary["status"] == "error"
            assert "not found" in summary["error"]

            # --- Test Case 2: Missing palette file ---
            image_path = tmp_path / "program.png"
            img = Image.new('RGB', (16, 16), color = 'red')
            img.save(image_path)
            non_existent_palette_path = tmp_path / "non_existent_palette.json"

            args = parser.parse_args([
                "color-compile",
                "--image", str(image_path),
                "--palette", str(non_existent_palette_path),
                "--out", str(output_program_path),
                "--format", "json"
            ])
            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cmd_color_compile(args)
            stdout_output = f.getvalue()
            assert exit_code == 1
            summary = json.loads(stdout_output)
            assert summary["status"] == "error"
            assert "not found" in summary["error"]

            # --- Test Case 3: Invalid palette file (malformed JSON) ---
            malformed_palette_path = tmp_path / "malformed_palette.json"
            with open(malformed_palette_path, 'w') as f:
                f.write("{invalid json")

            args = parser.parse_args([
                "color-compile",
                "--image", str(image_path),
                "--palette", str(malformed_palette_path),
                "--out", str(output_program_path),
                "--format", "json"
            ])
            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cmd_color_compile(args)
            stdout_output = f.getvalue()
            assert exit_code == 1
            summary = json.loads(stdout_output)
            assert summary["status"] == "error"
            assert "Invalid JSON" in summary["error"]

            # --- Test Case 4: Invalid palette file (unsupported version) ---
            unsupported_version_palette_path = tmp_path / "unsupported_version_palette.json"
            unsupported_palette_data = {
                "version": "palette-v99.9", # Unsupported version
                "tile_size": 16,
                "opcodes": {"FF0000": "PUSHI"},
                "immediate_mode": "rgb-to-int",
                "tolerance": 5.0
            }
            with open(unsupported_version_palette_path, 'w') as f:
                json.dump(unsupported_palette_data, f)

            args = parser.parse_args([
                "color-compile",
                "--image", str(image_path),
                "--palette", str(unsupported_version_palette_path),
                "--out", str(output_program_path),
                "--format", "json"
            ])
            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cmd_color_compile(args)
            stdout_output = f.getvalue()
            assert exit_code == 1
            summary = json.loads(stdout_output)
            assert summary["status"] == "error"
            assert "Unsupported palette version" in summary["error"]

            # --- Test Case 5: Unrecognized colors in PNG ---
            unrecognized_color_image_path = tmp_path / "unrecognized_color.png"
            img_unrecognized = Image.new('RGB', (16, 16), color = 'blue') # Blue is not in our palette
            img_unrecognized.save(unrecognized_color_image_path)

            args = parser.parse_args([
                "color-compile",
                "--image", str(unrecognized_color_image_path),
                "--palette", str(palette_path), # Use the valid red palette
                "--out", str(output_program_path),
                "--format", "json"
            ])
            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cmd_color_compile(args)
            stdout_output = f.getvalue()
            assert exit_code == 0 # Compilation should still succeed, but with unrecognized colors
            summary = json.loads(stdout_output)
            assert summary["status"] == "success"
            assert summary["unrecognized_colors"] == 1
            assert summary["tiles_processed"] == 1
            assert summary["instructions_generated"] == 1
            assert summary["grid_size"] == {"width": 1, "height": 1}
            assert "palette_hash" in summary # Check for presence, actual hash depends on content
            # The program should contain a NOP for the unrecognized color
            with open(output_program_path, 'r') as f:
                program_content = json.load(f)
            assert program_content == [{"opcode": "NOP", "comment": "Unrecognized color"}]


# This test should pass - it validates our TDD RED starting point
class TestRedPhaseValidation:
    """Ensure we're starting from the correct RED phase."""
    
    def test_color_commands_now_exist(self):
        """Confirm color commands have been successfully added (GREEN phase)."""
        parser = build_parser()
        
        # Color commands should now parse successfully
        try:
            args = parser.parse_args([
                "color-compile", "--image", "test.png", "--palette", "test.json", "--out", "test.json"
            ])
            assert args.command == "color-compile"
        except SystemExit:
            pytest.fail("color-compile command should parse successfully")
            
        try:
            args = parser.parse_args([
                "color-run", "--image", "test.png", "--palette", "test.json", "--trace", "test.json"  
            ])
            assert args.command == "color-run"
        except SystemExit:
            pytest.fail("color-run command should parse successfully")
            
        # Existing commands should still work
        try:
            args = parser.parse_args(["run", "--program", "test.json", "--trace", "test.json"])
            assert args.command == "run"
        except SystemExit:
            pytest.fail("Existing 'run' command should parse successfully")
            
        try:
            args = parser.parse_args(["verify", "--trace", "test.json"])
            assert args.command == "verify"
        except SystemExit:
            pytest.fail("Existing 'verify' command should parse successfully")