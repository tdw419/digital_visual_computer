"""
T006: Integration test for VM execution determinism
Based on specs/002-dvc-v0-1/spec.md user acceptance scenarios

This test MUST FAIL until VM implementation exists.
Tests that identical programs produce identical traces.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestVMDeterminism:
    """Integration tests for deterministic VM behavior"""
    
    @pytest.mark.integration
    def test_identical_programs_produce_identical_traces(self):
        """
        Given the same program with identical inputs,
        When I execute it multiple times,
        Then I get byte-for-byte identical execution traces
        """
        program = [
            {"op": "PUSHI", "arg": "10"},
            {"op": "PUSHI", "arg": "5"},
            {"op": "SUB"},
            {"op": "PUSHI", "arg": "2"}, 
            {"op": "MUL"},
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
        traces = []
        
        # Run the same program 3 times
        for run_id in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                program_file = Path(tmpdir) / f"program_{run_id}.json"
                trace_file = Path(tmpdir) / f"trace_{run_id}.json" 
                
                program_file.write_text(json.dumps(program, sort_keys=True))
                
                result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file),
                    "--deterministic-meta"
                ], capture_output=True, text=True)
                
                assert result.returncode == 0, f"Run {run_id} failed: {result.stderr}"
                assert trace_file.exists()
                
                trace_content = trace_file.read_text()
                traces.append(trace_content)
        
        # All traces must be byte-for-byte identical
        assert traces[0] == traces[1] == traces[2], "Traces are not identical"
        
        # Parse and verify structural identity
        parsed_traces = [json.loads(trace) for trace in traces]
        
        for i in range(1, 3):
            assert parsed_traces[0] == parsed_traces[i], f"Parsed trace {i} differs from trace 0"
            
            # Verify hash chains are identical
            assert (parsed_traces[0]["meta"]["final_root"] == 
                   parsed_traces[i]["meta"]["final_root"]), f"Final roots differ in run {i}"
            
            # Verify step-by-step hashes are identical
            for step_idx, (step0, step_i) in enumerate(zip(parsed_traces[0]["steps"], 
                                                          parsed_traces[i]["steps"])):
                assert step0["step_hash"] == step_i["step_hash"], \
                    f"Step {step_idx} hash differs between runs 0 and {i}"
    
    @pytest.mark.integration
    def test_cross_machine_determinism_simulation(self):
        """
        Simulate cross-machine determinism by varying execution context
        (This is a simulation since we can't test actual cross-machine)
        """
        program = [
            {"op": "PUSHI", "arg": "999"},
            {"op": "PUSHI", "arg": "7"},
            {"op": "DIV"},
            {"op": "PRINT"},
            {"op": "HALT"}
        ]
        
        traces = []
        
        # Simulate different "machines" by running in different temp directories
        # with different file paths and timing
        for machine_id in range(2):
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use different file names to simulate different machines
                program_file = Path(tmpdir) / f"machine_{machine_id}_program.json"
                trace_file = Path(tmpdir) / f"machine_{machine_id}_trace.json"
                
                # Write program identically
                program_file.write_text(json.dumps(program, sort_keys=True))
                
                result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file),
                    "--limit", "10000"  # Explicit limit
                ], capture_output=True, text=True)
                
                assert result.returncode == 0
                trace_data = json.loads(trace_file.read_text())
                traces.append(trace_data)
        
        # Verify computational results are identical (excluding timestamps)
        for field in ["halted", "faulted", "outputs", "final_root", "step_limit"]:
            assert traces[0]["meta"][field] == traces[1]["meta"][field], \
                f"Meta field '{field}' differs between machines"
        
        # Verify step-by-step execution is identical
        assert len(traces[0]["steps"]) == len(traces[1]["steps"])
        
        for i, (step0, step1) in enumerate(zip(traces[0]["steps"], traces[1]["steps"])):
            for field in ["index", "ip", "op", "arg", "stack_before", "stack_after", 
                         "output", "step_hash"]:
                if field in step0 or field in step1:
                    assert step0.get(field) == step1.get(field), \
                        f"Step {i} field '{field}' differs between machines"
    
    @pytest.mark.integration  
    def test_arithmetic_determinism(self):
        """Test that arithmetic operations produce consistent results"""
        # Test edge cases that might vary across platforms
        test_cases = [
            # Basic operations
            [{"op": "PUSHI", "arg": "2"}, {"op": "PUSHI", "arg": "3"}, {"op": "ADD"}, {"op": "PRINT"}, {"op": "HALT"}],
            # Division (truncate toward zero per research.md)
            [{"op": "PUSHI", "arg": "5"}, {"op": "PUSHI", "arg": "2"}, {"op": "DIV"}, {"op": "PRINT"}, {"op": "HALT"}],
            [{"op": "PUSHI", "arg": "-5"}, {"op": "PUSHI", "arg": "2"}, {"op": "DIV"}, {"op": "PRINT"}, {"op": "HALT"}],
            # Large numbers (arbitrary precision)
            [{"op": "PUSHI", "arg": "999999999999999999999"}, {"op": "PUSHI", "arg": "2"}, {"op": "MUL"}, {"op": "PRINT"}, {"op": "HALT"}],
        ]
        
        expected_outputs = ["5", "2", "-2", "1999999999999999999998"]
        
        for i, (program, expected_output) in enumerate(zip(test_cases, expected_outputs)):
            with tempfile.TemporaryDirectory() as tmpdir:
                program_file = Path(tmpdir) / f"arith_test_{i}.json"
                trace_file = Path(tmpdir) / f"arith_trace_{i}.json"
                
                program_file.write_text(json.dumps(program))
                
                result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file)
                ], capture_output=True, text=True)
                
                assert result.returncode == 0
                trace_data = json.loads(trace_file.read_text())
                assert trace_data["meta"]["outputs"] == [expected_output], \
                    f"Test case {i}: expected {expected_output}, got {trace_data['meta']['outputs']}"
    
    @pytest.mark.integration
    def test_hash_chain_consistency(self):
        """Test that hash chains are computed consistently"""
        program = [
            {"op": "PUSHI", "arg": "1"}, 
            {"op": "PUSHI", "arg": "1"},
            {"op": "ADD"},
            {"op": "HALT"}
        ]
        
        hash_chains = []
        
        # Run multiple times and collect hash chains
        for run in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                program_file = Path(tmpdir) / f"hash_test_{run}.json"
                trace_file = Path(tmpdir) / f"hash_trace_{run}.json"
                
                program_file.write_text(json.dumps(program))
                
                result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file)
                ], capture_output=True, text=True)
                
                assert result.returncode == 0
                trace_data = json.loads(trace_file.read_text())
                
                # Extract hash chain
                chain = [step["step_hash"] for step in trace_data["steps"]]
                hash_chains.append(chain)
        
        # All hash chains must be identical
        for i in range(1, 3):
            assert hash_chains[0] == hash_chains[i], f"Hash chain {i} differs from chain 0"
            
        # Verify final root consistency
        for run in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                program_file = Path(tmpdir) / f"final_test_{run}.json"
                trace_file = Path(tmpdir) / f"final_trace_{run}.json"
                
                program_file.write_text(json.dumps(program))
                
                result = subprocess.run([
                    "dvc", "run",
                    "--program", str(program_file),
                    "--trace", str(trace_file),
                    "--format", "json"
                ], capture_output=True, text=True)
                
                summary = json.loads(result.stdout)
                if run == 0:
                    expected_final_root = summary["final_root"]
                else:
                    assert summary["final_root"] == expected_final_root, \
                        f"Final root differs in run {run}"