from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dvc_core.pixeltext import encode_ptx1, decode_ptx1, PixelTextError

def _print_json(obj: dict) -> None:
    """Prints a dictionary as a JSON string to stdout."""
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")

def cmd_pixeltext_encode(args: argparse.Namespace) -> int:
    """Handler for the 'pixeltext-encode' command."""
    try:
        # Read the source file as bytes to preserve original content
        source_content = Path(args.input).read_text(encoding='utf-8')

        result = encode_ptx1(
            payload=source_content,
            output_path=Path(args.out),
            use_ecc=not args.no_ecc,
            lang=args.lang or "unknown"
        )

        if args.format == "json":
            _print_json(result)
        else:
            print(f"✅ Successfully encoded '{args.input}' to '{args.out}'")
            print(f"Source SHA256: {result['sha256_src']}")

        return 0
    except (PixelTextError, FileNotFoundError) as e:
        if args.format == "json":
            _print_json({"status": "error", "error": str(e)})
        else:
            sys.stderr.write(f"Error: {e}\n")
        return 1
    except Exception as e:
        if args.format == "json":
            _print_json({"status": "error", "error": f"An unexpected error occurred: {e}"})
        else:
            sys.stderr.write(f"An unexpected error occurred: {e}\n")
        return 2

def cmd_pixeltext_decode(args: argparse.Namespace) -> int:
    """Handler for the 'pixeltext-decode' command."""
    try:
        result = decode_ptx1(
            input_path=Path(args.input),
            strict=not args.no_strict
        )

        if args.format == "json":
            _print_json(result)
        else:
            print("✅ Verification successful.")
            print(f"Repairs made by ECC: {result['metadata'].get('repairs', 0)}")
            # If an output file is specified, write the source content to it
            if args.out:
                output_path = Path(args.out)
                if isinstance(result['content'], dict) and 'src' in result['content']:
                    output_path.write_text(result['content']['src'], encoding='utf-8')
                elif isinstance(result['content'], str):
                    output_path.write_text(result['content'], encoding='utf-8')
                else: # bytes
                    output_path.write_bytes(result['content'])
                print(f"Decoded content written to '{output_path}'")
            else:
                # Otherwise, print to stdout
                print("\n--- Decoded Content ---")
                if isinstance(result['content'], dict):
                    print(json.dumps(result['content'], indent=2))
                else:
                    print(result['content'])

        return 0
    except PixelTextError as e:
        if args.format == "json":
            _print_json({"status": "error", "verified": False, "error": str(e)})
        else:
            sys.stderr.write(f"Error: {e}\n")
        return 1
    except Exception as e:
        if args.format == "json":
            _print_json({"status": "error", "verified": False, "error": f"An unexpected error occurred: {e}"})
        else:
            sys.stderr.write(f"An unexpected error occurred: {e}\n")
        return 2