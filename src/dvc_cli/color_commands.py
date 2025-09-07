"""
CLI commands for color language features.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any
import hashlib

from color_lang.palette import ColorPalette
from color_lang.exceptions import ColorLangError
from color_lang.compiler import ColorCompiler


def cmd_color_compile(args: argparse.Namespace) -> int:
    """Handle dvc color-compile command."""
    try:
        # Load palette
        palette = ColorPalette.from_file(args.palette)
        
        # Calculate palette hash
        palette_json = json.dumps(palette.opcodes, sort_keys=True).encode('utf-8')
        palette_hash = hashlib.sha256(palette_json).hexdigest()

        # Check if image file exists
        image_path = Path(args.image)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {args.image}")
        
        # Instantiate compiler and compile
        compiler = ColorCompiler(palette)
        dvc_ir, compilation_summary_str = compiler.compile_and_summarize(str(image_path))
        
        # Write output program
        output_path = Path(args.out)
        with open(output_path, 'w') as f:
            json.dump(dvc_ir["program"], f, indent=2)
        
        # Create compilation summary
        summary = {
            "status": "success",
            "tiles_processed": len(dvc_ir["program"]),
            "instructions_generated": len(dvc_ir["program"]),
            "palette_hash": palette_hash,
            "program_path": str(output_path),
            "grid_size": dvc_ir["metadata"]["grid_size"],
            "unrecognized_colors": dvc_ir["metadata"]["unrecognized_colors"],
            "warnings": []
        }
        
        if getattr(args, 'format', None) == 'json':
            sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        else:
            sys.stdout.write(compilation_summary_str + "\n")
        
        return 0
        
    except ColorLangError as e:
        summary = {
            "status": "error",
            "error": str(e),
            "tiles_processed": 0,
            "program_path": None
        }
        if getattr(args, 'format', None) == 'json':
            sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        else:
            sys.stderr.write(f"Compilation error: {e}\n")
        return 1
    except Exception as e:
        if getattr(args, 'format', None) == 'json':
            summary = {
                "status": "error", 
                "error": str(e),
                "tiles_processed": 0,
                "program_path": None
            }
            sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        else:
            sys.stderr.write(f"I/O error: {e}\n")
        return 2


def cmd_color_run(args: argparse.Namespace) -> int:
    """Handle dvc color-run command."""
    try:
        # Load palette
        palette = ColorPalette.from_file(args.palette)
        
        # Calculate palette hash
        palette_json = json.dumps(palette.opcodes, sort_keys=True).encode('utf-8')
        palette_hash = hashlib.sha256(palette_json).hexdigest()

        # Check if image file exists
        image_path = Path(args.image)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Instantiate compiler and compile
        compiler = ColorCompiler(palette)
        dvc_ir = compiler.compile_png_to_dvc_ir(str(image_path)) # Changed here
        
        # TODO: Execute with DVC VM
        
        # Create trace with color provenance
        trace = {
            "meta": {
                "version": "dvc-trace-0.1",
                "halted": True, # Placeholder
                "faulted": False, # Placeholder
                "outputs": [], # Placeholder
                "final_root": "placeholder_hash", # Placeholder
                "color_provenance": {
                    "palette_hash": palette_hash, # Use calculated hash
                    "compiler_version": dvc_ir["metadata"]["compiler"],
                    "tile_size": palette.tile_size, # Get from palette
                    "grid_size": dvc_ir["metadata"]["grid_size"], # Changed here
                    "compilation_summary": {
                        "tiles_processed": len(dvc_ir["program"]),
                        "instructions_generated": len(dvc_ir["program"])
                    }
                }
            },
            "steps": [] # Placeholder for VM execution steps
        }
        
        # Write trace
        trace_path = Path(args.trace)
        with open(trace_path, 'w') as f:
            json.dump(trace, f, indent=2)
        
        # Create execution summary
        summary = {
            "status": "halted",
            "steps": 0,
            "outputs": [],
            "final_root": "placeholder_hash",
            "trace_path": str(trace_path),
            "compilation": {
                "tiles_processed": len(dvc_ir["program"]),
                "palette_hash": palette_hash,
                "grid_size": dvc_ir["metadata"]["grid_size"] # Changed here
            }
        }
        
        if getattr(args, 'format', None) == 'json':
            sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        
        return 0
        
    except ColorLangError as e:
        if getattr(args, 'format', None) == 'json':
            summary = {
                "status": "error",
                "error": str(e),
                "compilation": None
            }
            sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        else:
            sys.stderr.write(f"Compilation error: {e}\n")
        return 1
    except Exception as e:
        if getattr(args, 'format', None) == 'json':
            summary = {
                "status": "error",
                "error": str(e),
                "compilation": None
            }
            sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        else:
            sys.stderr.write(f"Error: {e}\n")
        return 2
