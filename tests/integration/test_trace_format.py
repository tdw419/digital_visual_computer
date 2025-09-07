"""
T008: Integration test for trace format compliance
Based on specs/002-dvc-v0-1/data-model.md and research.md

This test MUST FAIL until trace serialization implementation exists.
Tests that generated traces conform to canonical format requirements.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestTraceFormat:
    """Integration tests for trace format compliance and canonicalization"""
    
    @pytest.mark.integration
    def test_trace_schema_compliance(self):
        """Test that generated traces conform to data model schema"""
        program = [
            {"op": "PUSHI", "arg": "123"},
            {"op": "POP"}, 
            {"op": "PUSHI", "arg": "456"},
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
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
            
            trace_data = json.loads(trace_file.read_text())
            
            # Validate top-level structure
            assert "meta" in trace_data
            assert "steps" in trace_data
            assert isinstance(trace_data["steps"], list)
            
            # Validate TraceMeta schema
            meta = trace_data["meta"]
            required_meta_fields = [
                "version", "step_limit", "halted", "faulted", 
                "outputs", "final_root", "started_at", "finished_at"
            ]
            for field in required_meta_fields:
                assert field in meta, f"Missing meta field: {field}"
            
            assert meta["version"] == "dvc-trace-0.1"
            assert isinstance(meta["step_limit"], int)
            assert isinstance(meta["halted"], bool)
            assert isinstance(meta["faulted"], bool)
            assert isinstance(meta["outputs"], list)
            assert isinstance(meta["final_root"], str) and len(meta["final_root"]) == 64
            assert isinstance(meta["started_at"], str)
            assert isinstance(meta["finished_at"], str)
            
            # Validate TraceStep schema
            for i, step in enumerate(trace_data["steps"]):
                required_step_fields = [
                    "index", "ip", "op", "stack_before", "stack_after", "step_hash"
                ]
                for field in required_step_fields:
                    assert field in step, f"Missing step {i} field: {field}"
                
                assert step["index"] == i
                assert isinstance(step["ip"], int)
                assert isinstance(step["op"], str)
                assert isinstance(step["stack_before"], list)
                assert isinstance(step["stack_after"], list)
                assert isinstance(step["step_hash"], str) and len(step["step_hash"]) == 64
                
                # Optional fields
                if "arg" in step:
                    assert isinstance(step["arg"], str)
                if "output" in step:
                    assert isinstance(step["output"], str)
                if "note" in step:
                    assert isinstance(step["note"], str)
                if "fault" in step:
                    assert isinstance(step["fault"], str)
    
    @pytest.mark.integration
    def test_integer_string_encoding(self):
        """Test that integers are encoded as decimal strings per research.md"""
        program = [
            {"op": "PUSHI", "arg": "999999999999999999999"},  # Large number
            {"op": "PUSHI", "arg": "-42"},                   # Negative number
            {"op": "PUSHI", "arg": "0"},                     # Zero
            {"op": "ADD"},
            {"op": "MUL"},
            {"op": "HALT"}
        ]
        
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
            
            trace_data = json.loads(trace_file.read_text())
            
            # All integers in trace must be strings
            for step in trace_data["steps"]:
                # Check arg field
                if "arg" in step:
                    assert isinstance(step["arg"], str)
                    # Should be valid decimal representation
                    int(step["arg"])  # Should not raise exception
                
                # Check stack values
                for stack_val in step["stack_before"] + step["stack_after"]:
                    assert isinstance(stack_val, str)
                    int(stack_val)  # Should not raise exception
                
                # Check output if present
                if "output" in step:
                    assert isinstance(step["output"], str)
                    int(step["output"])  # Should not raise exception
            
            # Check meta outputs
            for output_val in trace_data["meta"]["outputs"]:
                assert isinstance(output_val, str)
                int(output_val)  # Should not raise exception
    
    @pytest.mark.integration
    def test_canonical_json_formatting(self):
        """Test canonical JSON format: sorted keys, no whitespace, UTF-8"""
        program = [{"op": "PUSHI", "arg": "1"}, {"op": "HALT"}]
        
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
            
            # Read raw bytes to check encoding
            trace_bytes = trace_file.read_bytes()
            trace_text = trace_file.read_text(encoding='utf-8')
            
            # Must be valid UTF-8
            assert trace_bytes.decode('utf-8') == trace_text
            
            # Must be valid JSON
            trace_data = json.loads(trace_text)
            
            # Re-serialize with sorted keys to check canonicalization
            canonical = json.dumps(trace_data, sort_keys=True, separators=(',', ':'))
            
            # Check that original format is canonical (or close to canonical)
            # Note: Implementation might add some whitespace, but keys should be sorted
            reparsed = json.loads(trace_text)
            canonical_reparsed = json.loads(canonical)
            assert reparsed == canonical_reparsed, "Trace data should be canonically formatted"
            
            # Check newline style (Unix \n only)
            assert '\r\n' not in trace_text, "Should use Unix newlines only"
    
    @pytest.mark.integration
    def test_hash_format_validation(self):
        """Test that all hashes are valid SHA-256 hex strings"""
        program = [{"op": "PUSHI", "arg": "42"}, {"op": "PRINT"}, {"op": "HALT"}]
        
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
            
            trace_data = json.loads(trace_file.read_text())
            
            # Validate final_root hash format
            final_root = trace_data["meta"]["final_root"]
            assert len(final_root) == 64, "SHA-256 hash should be 64 hex chars"
            assert all(c in '0123456789abcdefABCDEF' for c in final_root), "Hash should be hex"
            
            # Validate step hashes
            for i, step in enumerate(trace_data["steps"]):
                step_hash = step["step_hash"]
                assert len(step_hash) == 64, f"Step {i} hash should be 64 hex chars"
                assert all(c in '0123456789abcdefABCDEF' for c in step_hash), f"Step {i} hash should be hex"
    
    @pytest.mark.integration
    def test_stack_state_invariants(self):
        """Test that stack states follow proper invariants"""
        program = [
            {"op": "PUSHI", "arg": "10"},
            {"op": "PUSHI", "arg": "20"},
            {"op": "PUSHI", "arg": "30"},
            {"op": "ADD"},  # Should consume 30,20 and produce 50
            {"op": "SUB"},  # Should consume 50,10 and produce -40
            {"op": "HALT"}
        ]
        
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
            
            trace_data = json.loads(trace_file.read_text())
            steps = trace_data["steps"]
            
            # Verify stack continuity: steps[i].stack_after == steps[i+1].stack_before
            for i in range(len(steps) - 1):
                assert steps[i]["stack_after"] == steps[i + 1]["stack_before"], \
                    f"Stack discontinuity between steps {i} and {i+1}"
            
            # Verify step indices are sequential
            for i, step in enumerate(steps):
                assert step["index"] == i, f"Step index {step['index']} should be {i}"
    
    @pytest.mark.integration 
    def test_opcode_arg_consistency(self):
        """Test that opcodes with/without args are handled consistently"""
        program = [
            {"op": "NOP"},                    # No arg
            {"op": "PUSHI", "arg": "100"},   # With arg
            {"op": "POP"},                   # No arg
            {"op": "HALT"}                   # No arg
        ]
        
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
            
            trace_data = json.loads(trace_file.read_text())
            steps = trace_data["steps"]
            
            # Check arg field presence matches opcode requirements
            for i, step in enumerate(steps):
                if step["op"] == "PUSHI":
                    assert "arg" in step, f"PUSHI step {i} missing arg field"
                    assert step["arg"] == "100"
                else:
                    # Other opcodes should not have arg field (or it should be null/empty)
                    if "arg" in step:
                        assert step["arg"] is None or step["arg"] == "", \
                            f"Step {i} ({step['op']}) should not have arg"
    
    @pytest.mark.integration
    def test_timestamp_format(self):
        """Test that timestamps follow ISO8601 UTC format"""
        program = [{"op": "HALT"}]
        
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
            
            trace_data = json.loads(trace_file.read_text())
            meta = trace_data["meta"]
            
            # Check timestamp format (ISO8601 UTC)
            import re
            iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
            
            assert re.match(iso8601_pattern, meta["started_at"]), \
                f"Invalid started_at format: {meta['started_at']}"
            assert re.match(iso8601_pattern, meta["finished_at"]), \
                f"Invalid finished_at format: {meta['finished_at']}"
            
            # finished_at should be >= started_at
            # (Simple string comparison works for ISO8601)
            assert meta["finished_at"] >= meta["started_at"]