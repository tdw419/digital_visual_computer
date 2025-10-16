import json
import sys

def assemble(input_path, output_path):
    instructions = []
    with open(input_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            op = parts[0]
            arg = parts[1] if len(parts) > 1 else None
            instruction = {"op": op}
            if arg is not None:
                instruction["arg"] = arg
            instructions.append(instruction)

    with open(output_path, 'w') as f:
        json.dump(instructions, f, indent=4)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python asm.py <input.dvc> <output.json>")
        sys.exit(1)

    assemble(sys.argv[1], sys.argv[2])