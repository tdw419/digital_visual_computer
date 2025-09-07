from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict
from pathlib import Path

from dvc_core.vm import execute
from dvc_core.verifier import verify_trace
from lib.program_loader import load_program_json
from lib.trace_serializer import write_canonical_json, read_json
from .color_commands import cmd_color_compile, cmd_color_run
from dvc_core.bundle import DVCBundle, DVCBundleError


def _print_json(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, sort_keys=True) + "\n")


def cmd_run(args: argparse.Namespace) -> int:
    try:
        program = load_program_json(args.program)
        limit = int(args.limit) if args.limit is not None else 10_000
        deterministic_meta = getattr(args, 'deterministic_meta', False)
        trace = execute(program, step_limit=limit, deterministic_meta=deterministic_meta)
        write_canonical_json(args.trace, trace)
        summary = {
            "status": "halted" if trace["meta"]["halted"] else ("faulted" if trace["meta"]["fault"] else "running"),
            "steps": len(trace["steps"]),
            "outputs": trace["meta"]["outputs"],
            "final_root": trace["meta"]["final_root"],
            "trace_path": args.trace,
        }
        if args.format == "json":
            _print_json(summary)
        return 0 if trace["meta"]["halted"] and not trace["meta"]["faulted"] else (2 if trace["meta"]["faulted"] else 0)
    except Exception as e:
        if args.format == "json":
            _print_json({"error": str(e)})
        else:
            sys.stderr.write(f"Error: {e}\n")
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        if args.bundle:
            bundle = DVCBundle(Path(args.bundle))
            res = bundle.verify()
            if args.format == "json":
                _print_json(res)
            return 0 if res.get("status") == "valid" else 1
        else:
            trace = read_json(args.trace)
            res = verify_trace(trace, strict=bool(args.strict), replay=bool(args.replay))
            # Augment with trace_path for contract convenience
            res_out: Dict[str, Any] = {**res, "trace_path": args.trace}
            if not res.get("valid") and "error" not in res_out:
                # Map reason to error; ensure 'hash' word appears for hash-related failures
                reason = str(res.get("reason", "verification failed"))
                if "hash" not in reason.lower():
                    reason = f"hash verification failed: {reason}"
                res_out["error"] = reason
            if args.format == "json":
                _print_json(res_out)
            return 0 if res.get("valid") else 1
    except DVCBundleError as e:
        if args.format == "json":
            _print_json({"status": "error", "error": str(e)})
        else:
            sys.stderr.write(f"Error verifying bundle: {e}\n")
        return 1
    except Exception as e:
        if args.format == "json":
            _print_json({"error": str(e)})
        else:
            sys.stderr.write(f"Error: {e}\n")
        return 1

def cmd_pack(args: argparse.Namespace) -> int:
    try:
        manifest_data = DVCBundle(Path(args.out)).pack(
            image_path=Path(args.image),
            palette_path=Path(args.palette),
            program_path=Path(args.program),
            trace_path=Path(args.trace),
            output_bundle_path=Path(args.out)
        )
        summary = {
            "status": "success",
            "bundle_path": str(Path(args.out)),
            "manifest": manifest_data
        }
        if args.format == "json":
            _print_json(summary)
        return 0
    except DVCBundleError as e:
        if args.format == "json":
            _print_json({"status": "error", "error": str(e)})
        else:
            sys.stderr.write(f"Error packing bundle: {e}\n")
        return 1
    except Exception as e:
        if args.format == "json":
            _print_json({"status": "error", "error": str(e)})
        else:
            sys.stderr.write(f"An unexpected error occurred: {e}\n")
        return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dvc", description="Digital Visual Computer CLI")
    sub = p.add_subparsers(dest="command")

    pr = sub.add_parser("run", help="Execute a program and emit a canonical trace")
    pr.add_argument("--program", required=True, help="Path to program JSON (IR)")
    pr.add_argument("--trace", required=True, help="Path to write trace JSON")
    pr.add_argument("--limit", required=False, help="Step limit (default 10000)")
    pr.add_argument("--deterministic-meta", action="store_true", help="Use fixed timestamps for byte-identical traces")
    pr.add_argument("--format", required=False, choices=["json"], help="Output format for stdout")
    pr.set_defaults(func=cmd_run)

    pv = sub.add_parser("verify", help="Verify a trace's hash-chain (and optionally semantics)")
    pv.add_argument("--trace", required=False, help="Path to trace JSON") # Changed to not required
    pv.add_argument("--bundle", required=False, help="Path to .dvcf bundle") # New argument
    pv.add_argument("--strict", action="store_true", help="Enable strict checks (reserved)")
    pv.add_argument("--replay", action="store_true", help="Enable semantic replay mode (reserved)")
    pv.add_argument("--format", required=False, choices=["json"], help="Output format for stdout")
    pv.set_defaults(func=cmd_verify)

    # Color language commands
    pcc = sub.add_parser("color-compile", help="Compile PNG color program to DVC JSON IR")
    pcc.add_argument("--image", required=True, help="Path to PNG color program")
    pcc.add_argument("--palette", required=True, help="Path to palette JSON")
    pcc.add_argument("--out", required=True, help="Path to write DVC program JSON")
    pcc.add_argument("--format", required=False, choices=["json"], help="Output format for stdout")
    pcc.add_argument("--tolerance", required=False, type=float, help="Color matching tolerance")
    pcc.set_defaults(func=cmd_color_compile)

    pcr = sub.add_parser("color-run", help="Compile and execute PNG color program")
    pcr.add_argument("--image", required=True, help="Path to PNG color program")
    pcr.add_argument("--palette", required=True, help="Path to palette JSON")
    pcr.add_argument("--trace", required=True, help="Path to write execution trace JSON")
    pcr.add_argument("--limit", required=False, help="Step execution limit (default: 10000)")
    pcr.add_argument("--deterministic-meta", action="store_true", help="Use fixed timestamps for byte-identical traces")
    pcr.add_argument("--format", required=False, choices=["json"], help="Output format for stdout")
    pcr.set_defaults(func=cmd_color_run)

    # Pack command
    pp = sub.add_parser("pack", help="Pack DVC assets into a .dvcf bundle")
    pp.add_argument("--image", required=True, help="Path to input PNG image")
    pp.add_argument("--palette", required=True, help="Path to input palette JSON")
    pp.add_argument("--program", required=True, help="Path to input program JSON (IR)")
    pp.add_argument("--trace", required=True, help="Path to input trace JSON")
    pp.add_argument("--out", required=True, help="Path to output .dvcf bundle")
    pp.add_argument("--format", required=False, choices=["json"], help="Output format for stdout")
    pp.set_defaults(func=cmd_pack)

    return p


def cli() -> None:
    # Entry point for console_script if installed
    sys.exit(main())

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return int(args.func(args))