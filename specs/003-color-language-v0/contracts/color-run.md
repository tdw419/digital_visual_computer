# Contract — dvc color-run (v0.1)

Purpose: Compile and execute a PNG color program in one step, producing a DVC execution trace.

## Invocation  
```
dvc color-run --image <program.png> --palette <palette.json> --trace <out.json> [--deterministic-meta] [--format json]
```

## Inputs
- program.png: PNG image with colored tiles representing program instructions
- palette.json: JSON mapping RGB hex colors to opcodes and encoding rules
- --deterministic-meta: use fixed timestamps for byte-identical traces

## Outputs
- Writes canonical execution trace to <out.json>
- Stdout (when --format json): execution summary JSON (same as `dvc run`)
- Exit codes:
  - 0: successful execution (halted normally or hit step limit)
  - 1: compilation error (color/palette issues) 
  - 2: execution fault (division by zero, stack underflow) or I/O error (missing files, write permissions)

## Pipeline Process
1. **Color compilation**: PNG + palette → DVC JSON IR (internal)
2. **VM execution**: JSON IR → hash-chained execution trace
3. **Trace serialization**: canonical JSON format with provenance

## Example stdout (execution summary)
```json
{
  "status": "halted",
  "steps": 4,
  "outputs": ["5"],
  "final_root": "9163b9975ed21d194140a6f675041b48aa5a8bf1f6f3e8700e48c77425389a81",
  "trace_path": "trace.json",
  "compilation": {
    "tiles_processed": 4,
    "palette_hash": "a1b2c3d4e5f6...",
    "grid_size": {"width": 2, "height": 2}
  }
}
```

## Trace Provenance
Generated traces include additional metadata for color program audit:
```json
{
  "meta": {
    "version": "dvc-trace-0.1",
    "color_provenance": {
      "palette_hash": "a1b2c3d4e5f6...",
      "compiler_version": "dvc-color-v0.1",
      "tile_size": 16,
      "grid_size": {"width": 2, "height": 2},
      "compilation_summary": {
        "tiles_processed": 4,
        "instructions_generated": 4
      }
    },
    // ... standard trace metadata
  }
}
```

## Error Handling
- **Compilation errors**: Same as `dvc color-compile` (exit 1)
- **Execution faults**: Same as `dvc run` (exit 2, trace written with fault info)
- **Combined reporting**: Both compilation and execution status in summary JSON

## Bundle Integration
When used with future bundle format:
- Original PNG and palette.json preserved in assets/
- Compiled program.json stored in build/
- Full execution trace with color provenance in trace.json

## Determinism
- --deterministic-meta flag enables byte-identical traces across runs
- Identical PNG + palette + settings → identical execution results
- Compatible with existing DVC verification (`dvc verify --trace out.json`)