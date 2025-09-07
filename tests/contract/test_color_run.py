"""
Contract tests for dvc color-run command.
Tests the CLI interface matches the specification in contracts/color-run.md
"""

import json
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from src.dvc_cli.main import build_parser
from src.dvc_cli.color_commands import cmd_color_run

import io
from contextlib import redirect_stdout


class TestColorRunContract:
    """Test color-run CLI contract compliance."""

    # Removed test_color_run_command_not_implemented as the command now exists

    # @pytest.mark.skip(reason="Will implement in GREEN phase")
    def test_color_run_success_contract(self):
        """Test successful execution returns expected JSON format.
        
        This test defines the contract but will be skipped until implementation.
        """
        # Contract requirements from color-run.md:
        # 1. Inputs: --image <program.png> --palette <palette.json> --trace <out.json>
        # 2. Outputs: Execution trace file + execution summary to stdout  
        # 3. Exit codes: 0 (success), 1 (compilation error), 2 (execution fault), 3 (I/O error)
        # 4. Stdout format: {"status": "halted", "steps": N, "compilation": {...}, ...}
        # 5. Trace includes color_provenance metadata
        
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

            # Define output trace path
            output_trace_path = tmp_path / "trace.json"

            # Prepare args for cmd_color_run
            parser = build_parser()
            args = parser.parse_args([
                "color-run",
                "--image", str(image_path),
                "--palette", str(palette_path),
                "--trace", str(output_trace_path),
                "--format", "json" # Request JSON output for easier parsing
            ])

            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cmd_color_run(args)
            stdout_output = f.getvalue()

            # Assert exit code
            assert exit_code == 0

            # Assert output trace file content
            assert output_trace_path.exists()
            with open(output_trace_path, 'r') as f:
                trace_content = json.load(f)
            
            # Basic assertions on trace structure
            assert "meta" in trace_content
            assert "steps" in trace_content
            assert "color_provenance" in trace_content["meta"]
            assert trace_content["meta"]["color_provenance"]["compiler_version"] == "ColorCompiler-v0.1"
            assert trace_content["meta"]["color_provenance"]["tile_size"] == 16
            assert trace_content["meta"]["color_provenance"]["grid_size"] == {"width": 1, "height": 1}
            assert trace_content["meta"]["color_provenance"]["compilation_summary"]["tiles_processed"] == 1
            assert trace_content["meta"]["color_provenance"]["compilation_summary"]["instructions_generated"] == 1
            assert "palette_hash" in trace_content["meta"]["color_provenance"]

            # Assert stdout summary content
            summary = json.loads(stdout_output)
            assert summary["status"] == "halted"
            assert summary["steps"] == 0 # No VM execution yet
            assert summary["trace_path"] == str(output_trace_path)
            assert "compilation" in summary
            assert summary["compilation"]["tiles_processed"] == 1
            assert summary["compilation"]["grid_size"] == {"width": 1, "height": 1}
            assert "palette_hash" in summary["compilation"]

    @pytest.mark.skip(reason="Will implement in GREEN phase")
    def test_color_run_deterministic_traces(self):
        """Test --deterministic-meta flag produces byte-identical traces.
        
        This test defines determinism contract but will be skipped until implementation.
        """
        # Contract requirements:
        # - Same PNG + palette + --deterministic-meta → identical trace files
        # - Compatible with existing dvc verify command
        
        pass  # Will implement when color-run command exists

    @pytest.mark.skip(reason="Will implement in GREEN phase")
    def test_color_run_error_handling(self):
        """Test error cases and exit codes match contract.
        
        This test defines error handling contract but will be skipped until implementation.
        """
        # Contract requirements:
        # - Exit 1 for compilation errors (bad PNG/palette)
        # - Exit 2 for execution faults (division by zero, etc.)
        # - Exit 3 for I/O errors (missing files, write permissions)
        
        pass  # Will implement when color-run command exists