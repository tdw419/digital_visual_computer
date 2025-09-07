"""
T007: Integration test for hash chain verification
Based on specs/002-dvc-v0-1/spec.md acceptance scenarios

This test MUST FAIL until verification implementation exists.  
Tests end-to-end trace verification workflow.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestHashChainVerification:
    """Integration tests for trace verification and hash chain validation"""
    
    @pytest.mark.integration
    def test_run_and_verify_workflow(self):
        """
        Given a program execution that produces a trace,
        When another person runs verification on the trace,
        Then they get identical step-by-step hash confirmation
        """
        program = [
            {"op": "PUSHI", "arg": "7"},
            {"op": "PUSHI", "arg": "6"},
            {"op": "MUL"},
            {"op": "PUSHI", "arg": "2"},
            {"op": "ADD"}, 
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "execution_trace.json"
            
            program_file.write_text(json.dumps(program, sort_keys=True))
            
            # Step 1: Run program to generate trace
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            assert run_result.returncode == 0, f"Run failed: {run_result.stderr}"
            
            run_summary = json.loads(run_result.stdout)
            original_final_root = run_summary["final_root"]
            
            # Step 2: Verify the generated trace
            verify_result = subprocess.run([
                "dvc", "verify", 
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            assert verify_result.returncode == 0, f"Verify failed: {verify_result.stderr}"
            
            verify_summary = json.loads(verify_result.stdout)
            assert verify_summary["status"] == "valid"
            assert verify_summary["final_root"] == original_final_root
            assert verify_summary["steps"] == len(program)
    
    @pytest.mark.integration
    def test_tampered_trace_detection(self):
        """Test that verification detects tampered traces"""
        program = [{"op": "PUSHI", "arg": "42"}, {"op": "PRINT"}, {"op": "HALT"}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "trace.json"
            tampered_trace_file = Path(tmpdir) / "tampered_trace.json"
            
            program_file.write_text(json.dumps(program))
            
            # Generate valid trace
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert run_result.returncode == 0
            
            # Load and tamper with trace
            trace_data = json.loads(trace_file.read_text())
            
            # Tamper with output value but keep hash (should be detected)
            trace_data["meta"]["outputs"] = ["99"]  # Changed from "42"
            
            tampered_trace_file.write_text(json.dumps(trace_data, sort_keys=True))
            
            # Verification should detect tampering
            verify_result = subprocess.run([
                "dvc", "verify",
                "--trace", str(tampered_trace_file),
                "--format", "json"  
            ], capture_output=True, text=True)
            
            assert verify_result.returncode == 1, "Should detect tampering"
            
            verify_summary = json.loads(verify_result.stdout)
            assert verify_summary["status"] == "invalid"
    
    @pytest.mark.integration
    def test_hash_chain_break_detection(self):
        """Test detection of broken hash chains"""
        program = [
            {"op": "PUSHI", "arg": "1"},
            {"op": "PUSHI", "arg": "2"}, 
            {"op": "PUSHI", "arg": "3"},
            {"op": "ADD"},
            {"op": "ADD"},
            {"op": "HALT"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "trace.json"
            broken_trace_file = Path(tmpdir) / "broken_trace.json"
            
            program_file.write_text(json.dumps(program))
            
            # Generate valid trace
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert run_result.returncode == 0
            
            # Break hash chain by modifying a step hash
            trace_data = json.loads(trace_file.read_text())
            if len(trace_data["steps"]) > 1:
                # Change hash of middle step (break chain)
                trace_data["steps"][1]["step_hash"] = "ff" * 32  # Invalid hash
            
            broken_trace_file.write_text(json.dumps(trace_data, sort_keys=True))
            
            # Verification should detect broken chain
            verify_result = subprocess.run([
                "dvc", "verify",
                "--trace", str(broken_trace_file)
            ], capture_output=True, text=True)
            
            assert verify_result.returncode == 1, "Should detect broken hash chain"
    
    @pytest.mark.integration
    def test_verification_with_strict_mode(self):
        """Test verification in strict mode performs additional checks"""
        program = [{"op": "PUSHI", "arg": "100"}, {"op": "HALT"}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "trace.json"
            
            program_file.write_text(json.dumps(program))
            
            # Generate trace
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert run_result.returncode == 0
            
            # Verify in strict mode
            verify_result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file),
                "--strict",
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Should pass strict verification for valid trace
            assert verify_result.returncode == 0
            
            verify_summary = json.loads(verify_result.stdout)
            assert verify_summary["status"] == "valid"
    
    @pytest.mark.integration
    def test_multiple_trace_verification(self):
        """Test verification of multiple traces from different programs"""
        programs = [
            [{"op": "PUSHI", "arg": "10"}, {"op": "HALT"}],
            [{"op": "PUSHI", "arg": "5"}, {"op": "PUSHI", "arg": "5"}, {"op": "MUL"}, {"op": "HALT"}],
            [{"op": "NOP"}, {"op": "NOP"}, {"op": "HALT"}]
        ]
        
        trace_files = []
        
        # Generate multiple traces
        for i, program in enumerate(programs):
            with tempfile.TemporaryDirectory() as tmpdir:
                program_file = Path(tmpdir) / f"program_{i}.json"
                trace_file = Path(tmpdir) / f"trace_{i}.json"
                
                program_file.write_text(json.dumps(program))
                
                run_result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file)
                ], capture_output=True, text=True)
                
                assert run_result.returncode == 0
                
                # Copy trace to permanent location for verification
                perm_trace = Path(tmpdir).parent / f"perm_trace_{i}.json"
                trace_data = trace_file.read_text()
                perm_trace.write_text(trace_data)
                trace_files.append(perm_trace)
        
        # Verify all traces
        for i, trace_file in enumerate(trace_files):
            verify_result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert verify_result.returncode == 0, f"Trace {i} failed verification"
            
            # Clean up
            trace_file.unlink()
    
    @pytest.mark.integration
    def test_final_root_validation(self):
        """Test that final_root in meta matches last step hash"""
        program = [
            {"op": "PUSHI", "arg": "8"},
            {"op": "PUSHI", "arg": "3"},
            {"op": "SUB"},
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "program.json"
            trace_file = Path(tmpdir) / "trace.json"
            
            program_file.write_text(json.dumps(program))
            
            # Generate trace
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert run_result.returncode == 0
            
            # Verify final root matches last step
            trace_data = json.loads(trace_file.read_text())
            assert len(trace_data["steps"]) > 0
            
            final_root = trace_data["meta"]["final_root"]
            last_step_hash = trace_data["steps"][-1]["step_hash"]
            
            # This invariant should be validated by verification
            assert final_root == last_step_hash, "Final root should match last step hash"
            
            # Verification should confirm this
            verify_result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            assert verify_result.returncode == 0