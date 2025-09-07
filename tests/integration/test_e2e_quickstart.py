"""
T009: End-to-end test from quickstart.md
Based on specs/002-dvc-v0-1/quickstart.md

This test MUST FAIL until full implementation exists.
Tests the complete workflow described in quickstart documentation.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestE2EQuickstart:
    """End-to-end test following the quickstart workflow"""
    
    @pytest.mark.integration
    def test_quickstart_workflow(self):
        """
        Execute the complete quickstart workflow:
        1. Create a simple program (2 + 3)
        2. Run it with dvc run
        3. Verify the trace with dvc verify
        4. Confirm expected results
        """
        # Step 1: Create quickstart program from specs/002-dvc-v0-1/quickstart.md
        quickstart_program = [
            {"op": "PUSHI", "arg": "2"},
            {"op": "PUSHI", "arg": "3"}, 
            {"op": "ADD"},
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "quickstart_program.json"
            trace_file = Path(tmpdir) / "quickstart_trace.json"
            
            # Write the program
            program_file.write_text(json.dumps(quickstart_program, indent=2))
            
            # Step 2: Run the program
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Should succeed
            assert run_result.returncode == 0, f"Run failed: {run_result.stderr}"
            
            # Parse run summary
            run_summary = json.loads(run_result.stdout)
            
            # Verify run results match quickstart expectations
            assert run_summary["status"] == "halted"
            assert run_summary["steps"] == 5
            assert run_summary["outputs"] == ["5"]  # 2 + 3 = 5
            assert len(run_summary["final_root"]) == 64  # SHA-256 hex
            assert run_summary["trace_path"] == str(trace_file)
            
            # Verify trace file was created and is valid JSON
            assert trace_file.exists()
            trace_data = json.loads(trace_file.read_text())
            
            # Step 3: Verify the trace
            verify_result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file), 
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Should succeed
            assert verify_result.returncode == 0, f"Verify failed: {verify_result.stderr}"
            
            # Parse verify summary
            verify_summary = json.loads(verify_result.stdout)
            
            # Verify results match expectations
            assert verify_summary["status"] == "valid"
            assert verify_summary["steps"] == 5
            assert verify_summary["final_root"] == run_summary["final_root"]
            
            # Step 4: Detailed trace inspection (quickstart validation)
            assert trace_data["meta"]["version"] == "dvc-trace-0.1"
            assert trace_data["meta"]["halted"] is True
            assert trace_data["meta"]["faulted"] is False
            assert trace_data["meta"]["outputs"] == ["5"]
            assert len(trace_data["steps"]) == 5
            
            # Validate each step matches expected execution
            expected_steps = [
                {"op": "PUSHI", "arg": "2", "stack_after": ["2"]},
                {"op": "PUSHI", "arg": "3", "stack_after": ["2", "3"]},
                {"op": "ADD", "stack_after": ["5"]},
                {"op": "PRINT", "stack_after": [], "output": "5"},
                {"op": "HALT", "stack_after": []}
            ]
            
            for i, (actual_step, expected) in enumerate(zip(trace_data["steps"], expected_steps)):
                assert actual_step["index"] == i
                assert actual_step["ip"] == i
                assert actual_step["op"] == expected["op"]
                
                if "arg" in expected:
                    assert actual_step["arg"] == expected["arg"]
                
                assert actual_step["stack_after"] == expected["stack_after"]
                
                if "output" in expected:
                    assert actual_step["output"] == expected["output"]
                
                # Verify hash is present and valid
                assert "step_hash" in actual_step
                assert len(actual_step["step_hash"]) == 64
    
    @pytest.mark.integration
    def test_quickstart_arithmetic_variants(self):
        """Test quickstart with different arithmetic operations"""
        test_cases = [
            # (program, expected_output, description)
            (
                [{"op": "PUSHI", "arg": "10"}, {"op": "PUSHI", "arg": "3"}, {"op": "SUB"}, {"op": "PRINT"}, {"op": "HALT"}],
                "7", 
                "subtraction"
            ),
            (
                [{"op": "PUSHI", "arg": "6"}, {"op": "PUSHI", "arg": "4"}, {"op": "MUL"}, {"op": "PRINT"}, {"op": "HALT"}],
                "24",
                "multiplication" 
            ),
            (
                [{"op": "PUSHI", "arg": "15"}, {"op": "PUSHI", "arg": "3"}, {"op": "DIV"}, {"op": "PRINT"}, {"op": "HALT"}],
                "5",
                "division"
            ),
        ]
        
        for i, (program, expected_output, description) in enumerate(test_cases):
            with tempfile.TemporaryDirectory() as tmpdir:
                program_file = Path(tmpdir) / f"test_{i}_{description}.json"
                trace_file = Path(tmpdir) / f"trace_{i}_{description}.json"
                
                program_file.write_text(json.dumps(program))
                
                # Run program
                run_result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file),
                    "--format", "json"
                ], capture_output=True, text=True)
                
                assert run_result.returncode == 0, f"{description} run failed: {run_result.stderr}"
                
                run_summary = json.loads(run_result.stdout)
                assert run_summary["outputs"] == [expected_output], \
                    f"{description}: expected {expected_output}, got {run_summary['outputs']}"
                
                # Verify trace
                verify_result = subprocess.run([
                    "dvc", "verify",
                    "--trace", str(trace_file)
                ], capture_output=True, text=True)
                
                assert verify_result.returncode == 0, f"{description} verify failed: {verify_result.stderr}"
    
    @pytest.mark.integration
    def test_quickstart_error_handling(self):
        """Test quickstart workflow with error conditions"""
        # Test stack underflow
        underflow_program = [
            {"op": "POP"},  # Should fail - empty stack
            {"op": "HALT"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "underflow_program.json"
            trace_file = Path(tmpdir) / "underflow_trace.json"
            
            program_file.write_text(json.dumps(underflow_program))
            
            # Run should exit with fault code
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file),
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Should exit 2 (fault) but still produce trace
            assert run_result.returncode == 2
            assert trace_file.exists()
            
            run_summary = json.loads(run_result.stdout)
            assert run_summary["status"] == "faulted"
            
            # Verify the fault trace
            verify_result = subprocess.run([
                "dvc", "verify",
                "--trace", str(trace_file)
            ], capture_output=True, text=True)
            
            # Verification should succeed even for fault traces
            assert verify_result.returncode == 0
    
    @pytest.mark.integration
    def test_quickstart_step_limit(self):
        """Test quickstart with step limits"""
        # Create program that would run many steps
        long_program = []
        for i in range(50):  # Many NOPs
            long_program.append({"op": "NOP"})
        long_program.append({"op": "HALT"})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            program_file = Path(tmpdir) / "long_program.json"
            trace_file = Path(tmpdir) / "long_trace.json"
            
            program_file.write_text(json.dumps(long_program))
            
            # Run with small step limit
            run_result = subprocess.run([
                "dvc", "run",
                "--program", str(program_file),
                "--trace", str(trace_file),
                "--limit", "10",  # Should halt at limit
                "--format", "json"
            ], capture_output=True, text=True)
            
            # Should succeed but not complete program
            assert run_result.returncode == 0
            
            run_summary = json.loads(run_result.stdout)
            assert run_summary["steps"] == 10  # Should stop at limit
            
            trace_data = json.loads(trace_file.read_text())
            assert trace_data["meta"]["step_limit"] == 10
            assert len(trace_data["steps"]) == 10
    
    @pytest.mark.integration
    def test_quickstart_reproducibility(self):
        """Test that quickstart produces identical results on repeated runs"""
        program = [
            {"op": "PUSHI", "arg": "7"},
            {"op": "PUSHI", "arg": "8"}, 
            {"op": "ADD"},
            {"op": "PUSHI", "arg": "3"},
            {"op": "MUL"}, 
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
        traces = []
        summaries = []
        
        # Run same program 3 times
        for run in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                program_file = Path(tmpdir) / f"repro_{run}.json"
                trace_file = Path(tmpdir) / f"repro_trace_{run}.json"
                
                program_file.write_text(json.dumps(program, sort_keys=True))
                
                run_result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file),
                    "--format", "json"
                ], capture_output=True, text=True)
                
                assert run_result.returncode == 0
                
                trace_content = trace_file.read_text()
                traces.append(trace_content)
                
                summary = json.loads(run_result.stdout)
                summaries.append(summary)
        
        # All runs should produce identical results
        assert summaries[0]["final_root"] == summaries[1]["final_root"] == summaries[2]["final_root"]
        assert summaries[0]["outputs"] == summaries[1]["outputs"] == summaries[2]["outputs"]
        
        # Parse traces and compare structural content (excluding timestamps)
        parsed_traces = [json.loads(trace) for trace in traces]
        
        for i in range(1, 3):
            # Compare everything except timestamps
            for field in ["version", "step_limit", "halted", "faulted", "outputs", "final_root"]:
                assert parsed_traces[0]["meta"][field] == parsed_traces[i]["meta"][field]
            
            # Compare all steps
            assert parsed_traces[0]["steps"] == parsed_traces[i]["steps"]