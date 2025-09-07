"""
Test utilities for generating valid synthetic traces.
Helps contract tests create realistic trace data without full VM execution.
"""

from typing import List, Dict, Any, Optional
from dvc_core.hash_chain import step_hash, ZERO_HASH


def create_synthetic_trace(
    program_steps: List[Dict[str, Any]], 
    outputs: Optional[List[str]] = None,
    halted: bool = True,
    faulted: bool = False,
    step_limit: int = 10000
) -> Dict[str, Any]:
    """
    Create a synthetic trace with valid hash chain from a minimal step description.
    
    Args:
        program_steps: List of step dictionaries with at least 'op', optional 'arg', 'output'
        outputs: List of output values (defaults to collecting from steps)
        halted: Whether execution halted normally
        faulted: Whether execution faulted
        step_limit: Step limit used
        
    Returns:
        Complete trace dict with valid hash chain
    """
    if outputs is None:
        outputs = []
        for step in program_steps:
            if "output" in step:
                outputs.append(step["output"])
    
    steps = []
    prev_hash = ZERO_HASH
    stack = []
    
    for i, step_spec in enumerate(program_steps):
        # Build step with default values
        step = {
            "index": i,
            "ip": i,
            "op": step_spec["op"],
            "stack_before": stack.copy(),
        }
        
        # Add optional fields
        if "arg" in step_spec:
            step["arg"] = step_spec["arg"]
        if "output" in step_spec:
            step["output"] = step_spec["output"]
        if "note" in step_spec:
            step["note"] = step_spec["note"]
        if "fault" in step_spec:
            step["fault"] = step_spec["fault"]
        
        # Simulate stack operations for realistic stack_after
        if step_spec["op"] == "PUSHI" and "arg" in step_spec:
            stack.append(step_spec["arg"])
        elif step_spec["op"] == "POP" and stack:
            stack.pop()
        elif step_spec["op"] in ["ADD", "SUB", "MUL", "DIV"] and len(stack) >= 2:
            b = stack.pop()
            a = stack.pop()
            if step_spec["op"] == "ADD":
                result = str(int(a) + int(b))
            elif step_spec["op"] == "SUB":
                result = str(int(a) - int(b))
            elif step_spec["op"] == "MUL":
                result = str(int(a) * int(b))
            elif step_spec["op"] == "DIV" and int(b) != 0:
                result = str(int(int(a) / int(b)))  # Truncate toward zero
            else:
                result = "0"  # Default for edge cases
            stack.append(result)
        elif step_spec["op"] == "PRINT" and stack:
            stack.pop()
        
        step["stack_after"] = stack.copy()
        
        # Compute valid hash for this step
        hash_dict = step.copy()  # Don't include step_hash in computation
        computed_hash = step_hash(hash_dict, prev_hash)
        step["step_hash"] = computed_hash
        
        steps.append(step)
        prev_hash = computed_hash
    
    # Build complete trace
    trace = {
        "meta": {
            "version": "dvc-trace-0.1",
            "step_limit": step_limit,
            "halted": halted,
            "faulted": faulted,
            "outputs": outputs,
            "final_root": prev_hash if steps else ZERO_HASH,
            "started_at": "2025-01-07T12:00:00Z",  # Fixed timestamp for testing
            "finished_at": "2025-01-07T12:00:01Z"
        },
        "steps": steps
    }
    
    return trace


def create_simple_valid_trace() -> Dict[str, Any]:
    """Create a simple valid trace for basic contract testing."""
    return create_synthetic_trace([
        {"op": "PUSHI", "arg": "42"},
        {"op": "PRINT", "output": "42"},
        {"op": "HALT"}
    ], outputs=["42"])


def create_arithmetic_trace() -> Dict[str, Any]:
    """Create a valid trace with arithmetic operations."""
    return create_synthetic_trace([
        {"op": "PUSHI", "arg": "2"},
        {"op": "PUSHI", "arg": "3"},
        {"op": "ADD"},
        {"op": "PRINT", "output": "5"},
        {"op": "HALT"}
    ], outputs=["5"])


def create_fault_trace() -> Dict[str, Any]:
    """Create a valid trace that ends in a fault."""
    return create_synthetic_trace([
        {"op": "PUSHI", "arg": "5"},
        {"op": "PUSHI", "arg": "0"}, 
        {"op": "DIV", "fault": "division by zero"}
    ], outputs=[], halted=False, faulted=True)