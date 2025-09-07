"""
T004: Contract test for `dvc run` command
Based on specs/002-dvc-v0-1/contracts/dvc-run.md

This test MUST FAIL until CLI implementation exists.
Tests the CLI as an API with defined inputs/outputs.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestDvcRunContract:
    """Contract tests for dvc run command based on CLI specification"""
    
    def test_dvc_run_basic_program_success(self):
        """Test dvc run with simple arithmetic program - should exit 0"""
        program = [
            {"op": "PUSHI", "arg": "2"},
            {"op": "PUSHI", "arg": "3"},
            {"op": "ADD"},
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "trace.json"
            
            # Write program file
            program_file.write_text(json.dumps(program, indent=2))
            
            # Run dvc command
            result = subprocess.run([
                "dvc", "run", 
                "--program", str(program_file),
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Contract requirements
            assert result.returncode == 0, f"Expected success, got: {result.stderr}"
            
            # Trace file must exist
            assert trace_file.exists(), "Trace file was not created"
            
            # Stdout must contain summary JSON
            summary = json.loads(result.stdout)
            assert summary["status"] == "halted"
            assert summary["steps"] == 5
            assert summary["outputs"] == ["5"]
            assert len(summary["final_root"]) == 64  # SHA-256 hex
            assert summary["trace_path"] == str(trace_file)
            
            # Trace must be valid JSON with required structure
            trace_data = json.loads(trace_file.read_text())
            assert "meta" in trace_data
            assert "steps" in trace_data
            assert trace_data["meta"]["version"] == "dvc-trace-0.1"
            assert trace_data["meta"]["halted"] is True
            assert trace_data["meta"]["faulted"] is False
            assert len(trace_data["steps"]) == 5
    
    def test_dvc_run_with_step_limit(self):
        """Test dvc run with custom step limit"""
        program = [{"op": "NOP"}, {"op": "HALT"}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "trace.json"
            
            program_file.write_text(json.dumps(program))
            
            result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file), 
                "--limit", "100"
            ], capture_output=True, text=True)
            
            assert result.returncode == 0
            
            # Check trace contains correct step limit
            trace_data = json.loads(trace_file.read_text())
            assert trace_data["meta"]["step_limit"] == 100
    
    def test_dvc_run_division_by_zero_fault(self):
        """Test dvc run handles division by zero - should exit 2"""
        program = [
            {"op": "PUSHI", "arg": "5"},
            {"op": "PUSHI", "arg": "0"},
            {"op": "DIV"},
            {"op": "HALT"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "trace.json"
            
            program_file.write_text(json.dumps(program))
            
            result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Contract: exit 2 for VM faults, trace still written
            assert result.returncode == 2
            assert trace_file.exists()
            
            # Summary should indicate fault
            summary = json.loads(result.stdout)
            assert summary["status"] == "faulted"
            
            # Trace should record fault
            trace_data = json.loads(trace_file.read_text())
            assert trace_data["meta"]["faulted"] is True
            assert any("fault" in step for step in trace_data["steps"])
    
    def test_dvc_run_malformed_program_error(self):
        """Test dvc run with malformed program JSON - should exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "bad_program.json"
            trace_file = Path(tmpdir) / "trace.json"
            
            # Invalid JSON
            program_file.write_text("{ invalid json }")
            
            result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            # Contract: exit 1 for I/O and parsing errors
            assert result.returncode == 1
    
    def test_dvc_run_missing_program_file(self):
        """Test dvc run with missing program file - should exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing.json"
            trace_file = Path(tmpdir) / "trace.json"
            
            result = subprocess.run([
                "dvc", "run",
                "--program", str(missing_file),
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert result.returncode == 1
    
    def test_dvc_run_canonical_trace_format(self):
        """Test that trace output follows canonical JSON format requirements"""
        program = [{"op": "PUSHI", "arg": "42"}, {"op": "HALT"}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json" 
            trace_file = Path(tmpdir) / "trace.json"
            
            program_file.write_text(json.dumps(program))
            
            result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert result.returncode == 0
            
            # Check canonical format requirements
            trace_text = trace_file.read_text()
            trace_data = json.loads(trace_text)
            
            # Integers must be strings (per research.md)
            for step in trace_data["steps"]:
                if "arg" in step:
                    assert isinstance(step["arg"], str)
                assert all(isinstance(x, str) for x in step["stack_before"])
                assert all(isinstance(x, str) for x in step["stack_after"])
            
            # UTF-8 encoding, proper newlines
            assert trace_file.read_bytes().decode('utf-8') == trace_text
            assert "\r\n" not in trace_text  # Only \n newlines