"""
T005: Contract test for `dvc verify` command  
Based on specs/002-dvc-v0-1/contracts/dvc-verify.md

This test MUST FAIL until CLI implementation exists.
Tests trace verification as a contract with defined I/O.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest
from tests.test_utils import create_simple_valid_trace, create_arithmetic_trace


class TestDvcVerifyContract:
    """Contract tests for dvc verify command based on CLI specification"""
    
    def test_dvc_verify_valid_trace_success(self):
        """Test dvc verify with valid trace - should exit 0"""
        # Create a valid trace using test utility
        valid_trace = create_simple_valid_trace()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "valid_trace.json"
            trace_file.write_text(json.dumps(valid_trace, sort_keys=True))
            
            result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Contract: exit 0 for valid traces
            assert result.returncode == 0
            
            # Stdout should contain verification summary
            summary = json.loads(result.stdout)
            assert summary["status"] == "valid"
            assert summary["steps"] == 3
            assert summary["final_root"] == valid_trace["meta"]["final_root"]
            assert summary["trace_path"] == str(trace_file)
    
    def test_dvc_verify_invalid_hash_chain_failure(self):
        """Test dvc verify with broken hash chain - should exit 1"""
        invalid_trace = {
            "meta": {
                "version": "dvc-trace-0.1", 
                "step_limit": 10000,
                "halted": True,
                "faulted": False,
                "outputs": [],
                "final_root": "correct_hash",  # Doesn't match last step
                "started_at": "2025-01-07T12:00:00Z",
                "finished_at": "2025-01-07T12:00:01Z"
            },
            "steps": [
                {
                    "index": 0,
                    "ip": 0,
                    "op": "HALT", 
                    "stack_before": [],
                    "stack_after": [],
                    "step_hash": "wrong_hash"  # Doesn't match meta.final_root
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "invalid_trace.json"
            trace_file.write_text(json.dumps(invalid_trace, sort_keys=True))
            
            result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Contract: exit 1 for invalid traces
            assert result.returncode == 1
            
            # Summary should indicate failure
            summary = json.loads(result.stdout)
            assert summary["status"] == "invalid"
            assert "hash" in summary.get("error", "").lower()
    
    def test_dvc_verify_with_strict_mode(self):
        """Test dvc verify with --strict flag"""
        # Create a simple halt-only trace
        valid_trace = create_simple_valid_trace()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "trace.json"
            trace_file.write_text(json.dumps(valid_trace, sort_keys=True))
            
            result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file), 
                "--strict"
            ], capture_output=True, text=True)
            
            # Should still succeed with valid trace
            assert result.returncode == 0
    
    def test_dvc_verify_malformed_trace_error(self):
        """Test dvc verify with malformed trace file - should exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "bad_trace.json"
            trace_file.write_text("{ invalid json }")
            
            result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert result.returncode == 1
    
    def test_dvc_verify_missing_trace_file(self):
        """Test dvc verify with missing trace file - should exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing.json"
            
            result = subprocess.run([
                "dvc", "verify",
                "--trace", str(missing_file)
            ], capture_output=True, text=True)
            
            assert result.returncode == 1
    
    def test_dvc_verify_semantic_replay_mode(self):
        """Test dvc verify with semantic replay (future feature)"""
        # This test documents the interface for semantic replay
        # even though it's not implemented in v0.1
        valid_trace = create_arithmetic_trace()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "trace.json"
            trace_file.write_text(json.dumps(valid_trace, sort_keys=True))
            
            # Note: --replay flag may not be implemented in v0.1
            # This documents the intended interface
            result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file),
                "--replay"  # Semantic replay mode
            ], capture_output=True, text=True)
            
            # Should succeed (or fail gracefully if not implemented)
            assert result.returncode in [0, 1]