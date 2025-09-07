from __future__ import annotations

from typing import Dict, Any

from .hash_chain import step_hash, ZERO_HASH
from .trace_models import step_to_ordered_dict


def verify_trace(trace: Dict[str, Any], strict: bool = False, replay: bool = False) -> Dict[str, Any]:
    meta = trace.get("meta", {})
    steps = trace.get("steps", [])
    
    # Basic validation: final_root should match last step hash
    if not steps:
        expected_final = ZERO_HASH
    else:
        expected_final = steps[-1].get("step_hash", "")
    
    if meta.get("final_root") != expected_final:
        return {
            "status": "invalid",
            "valid": False,
            "error": "final_root does not match last step hash",
            "final_root": meta.get("final_root", ""),
            "steps": len(steps),
            "faulted": bool(meta.get("faulted", False)),
            "halted": bool(meta.get("halted", False)),
        }

    # Enhanced validation: check hash chain integrity
    # This detects tampering and broken chains
    prev_hash = ZERO_HASH
    for i, step in enumerate(steps):
        # Validate required fields
        required_fields = ["index", "ip", "op", "stack_before", "stack_after", "step_hash"]
        for field in required_fields:
            if field not in step:
                return {
                    "status": "invalid",
                    "valid": False,
                    "error": f"missing field {field} at step {i}",
                    "final_root": expected_final,
                    "steps": len(steps),
                    "faulted": bool(meta.get("faulted", False)),
                    "halted": bool(meta.get("halted", False)),
                }
        
        # Recompute hash for this step
        # Create ordered dict without step_hash field
        step_dict = {
            "index": step["index"],
            "ip": step["ip"],
            "op": step["op"],
        }
        if "arg" in step and step["arg"] is not None:
            step_dict["arg"] = step["arg"]
        step_dict["stack_before"] = step["stack_before"]
        step_dict["stack_after"] = step["stack_after"]
        if "output" in step and step["output"] is not None:
            step_dict["output"] = step["output"]
        if "note" in step and step["note"] is not None:
            step_dict["note"] = step["note"]
        if "fault" in step and step["fault"] is not None:
            step_dict["fault"] = step["fault"]
        
        computed_hash = step_hash(step_dict, prev_hash)
        claimed_hash = step.get("step_hash", "")
        
        if computed_hash != claimed_hash:
            return {
                "status": "invalid", 
                "valid": False,
                "error": f"hash chain broken at step {i}: expected {computed_hash}, got {claimed_hash}",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }
        
        prev_hash = computed_hash

    # Validate metadata consistency with steps
    # Collect outputs from steps
    step_outputs = []
    for step in steps:
        if "output" in step and step["output"] is not None:
            step_outputs.append(step["output"])
    
    # Check if meta.outputs matches step outputs
    meta_outputs = meta.get("outputs", [])
    if step_outputs != meta_outputs:
        return {
            "status": "invalid",
            "valid": False,
            "error": f"metadata outputs {meta_outputs} do not match step outputs {step_outputs}",
            "final_root": expected_final,
            "steps": len(steps),
            "faulted": bool(meta.get("faulted", False)),
            "halted": bool(meta.get("halted", False)),
        }

    # Validate color_provenance if present
    color_provenance = meta.get("color_provenance")
    if color_provenance:
        required_provenance_fields = [
            "palette_hash", 
            "compiler_version", 
            "tile_size", 
            "grid_size", 
            "compilation_summary"
        ]
        for field in required_provenance_fields:
            if field not in color_provenance:
                return {
                    "status": "invalid",
                    "valid": False,
                    "error": f"color_provenance missing required field: {field}",
                    "final_root": expected_final,
                    "steps": len(steps),
                    "faulted": bool(meta.get("faulted", False)),
                    "halted": bool(meta.get("halted", False)),
                }
        
        # Validate types and values
        if not isinstance(color_provenance["palette_hash"], str) or not color_provenance["palette_hash"]:
            return {
                "status": "invalid",
                "valid": False,
                "error": "color_provenance.palette_hash is invalid",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }
        if not isinstance(color_provenance["compiler_version"], str) or not color_provenance["compiler_version"]:
            return {
                "status": "invalid",
                "valid": False,
                "error": "color_provenance.compiler_version is invalid",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }
        if not isinstance(color_provenance["tile_size"], int) or color_provenance["tile_size"] <= 0:
            return {
                "status": "invalid",
                "valid": False,
                "error": "color_provenance.tile_size is invalid",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }
        
        grid_size = color_provenance["grid_size"]
        if not isinstance(grid_size, dict) or "width" not in grid_size or "height" not in grid_size:
            return {
                "status": "invalid",
                "valid": False,
                "error": "color_provenance.grid_size is invalid",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }
        if not isinstance(grid_size["width"], int) or grid_size["width"] <= 0 or \
           not isinstance(grid_size["height"], int) or grid_size["height"] <= 0:
            return {
                "status": "invalid",
                "valid": False,
                "error": "color_provenance.grid_size dimensions are invalid",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }

        compilation_summary = color_provenance["compilation_summary"]
        if not isinstance(compilation_summary, dict) or \
           "tiles_processed" not in compilation_summary or \
           "instructions_generated" not in compilation_summary:
            return {
                "status": "invalid",
                "valid": False,
                "error": "color_provenance.compilation_summary is invalid",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }
        if not isinstance(compilation_summary["tiles_processed"], int) or compilation_summary["tiles_processed"] < 0 or \
           not isinstance(compilation_summary["instructions_generated"], int) or compilation_summary["instructions_generated"] < 0:
            return {
                "status": "invalid",
                "valid": False,
                "error": "color_provenance.compilation_summary counts are invalid",
                "final_root": expected_final,
                "steps": len(steps),
                "faulted": bool(meta.get("faulted", False)),
                "halted": bool(meta.get("halted", False)),
            }

    # Additional strict mode checks
    if strict:
        # Verify step indices are sequential
        for i, step in enumerate(steps):
            if step.get("index") != i:
                return {
                    "status": "invalid",
                    "valid": False,
                    "error": f"step index mismatch at position {i}: expected {i}, got {step.get('index')}",
                    "final_root": expected_final,
                    "steps": len(steps),
                    "faulted": bool(meta.get("faulted", False)),
                    "halted": bool(meta.get("halted", False)),
                }
        
        # Verify stack continuity
        for i in range(len(steps) - 1):
            if steps[i]["stack_after"] != steps[i + 1]["stack_before"]:
                return {
                    "status": "invalid",
                    "valid": False,
                    "error": f"stack discontinuity between steps {i} and {i + 1}",
                    "final_root": expected_final,
                    "steps": len(steps),
                    "faulted": bool(meta.get("faulted", False)),
                    "halted": bool(meta.get("halted", False)),
                }

    # Replay mode (reserved): no-op success path in v0.1
    return {
        "status": "valid",
        "valid": True,
        "final_root": expected_final,
        "steps": len(steps),
        "faulted": bool(meta.get("faulted", False)),
        "halted": bool(meta.get("halted", False)),
    }