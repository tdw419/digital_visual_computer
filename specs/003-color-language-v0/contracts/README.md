# Color Language v0.1 - CLI Contracts

This directory defines the command-line interface contracts for DVC Color Language features.

## Commands Overview

**dvc color-compile**: Compile PNG color program to DVC JSON IR
- Input: PNG image + palette.json  
- Output: DVC program.json + compilation summary
- Use case: Separate compilation for inspection, reuse, or debugging

**dvc color-run**: Compile and execute PNG color program  
- Input: PNG image + palette.json
- Output: Execution trace + combined summary
- Use case: One-step execution for typical workflows

## Integration with Core DVC

Color language commands integrate seamlessly with existing DVC workflow:

```bash
# Traditional workflow
dvc run --program program.json --trace trace.json
dvc verify --trace trace.json

# Color language workflow  
dvc color-run --image program.png --palette palette.json --trace trace.json
dvc verify --trace trace.json  # Same verification!

# Mixed workflow
dvc color-compile --image program.png --palette palette.json --out program.json
dvc run --program program.json --trace trace.json  # Standard execution
```

## Color Program Requirements

All color programs must include:
1. **PNG image**: RGB/RGBA format, max 1024×1024 pixels
2. **palette.json**: Valid palette schema with opcode mappings  
3. **Grid alignment**: Image dimensions divisible by tile_size (default 16×16)

## Determinism Guarantees

- Same PNG + palette → same compilation output
- --deterministic-meta flag for byte-identical traces
- Compatible with existing DVC verification system
- Cross-machine reproducibility maintained

## Bundle Compatibility

Color programs integrate with future .dvcf bundle format:
- assets/program.png (original visual program)
- assets/palette.json (color mappings) 
- build/program.json (compiled IR)
- trace.json (execution with color provenance)

This preserves both human readability (colors) and machine verifiability (hashes).