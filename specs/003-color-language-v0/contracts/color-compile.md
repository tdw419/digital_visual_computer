# Contract — dvc color-compile (v0.1)

Purpose: Compile a PNG color program into DVC JSON IR using palette-driven opcode mapping.

## Invocation
```
dvc color-compile --image <program.png> --palette <palette.json> --out <program.json> [--format json]
```

## Inputs
- program.png: PNG image with colored tiles representing program instructions
- palette.json: JSON mapping RGB hex colors to opcodes and encoding rules

## Outputs
- Writes compiled DVC JSON IR program to <program.json>  
- Stdout (when --format json): compilation summary JSON
- Exit codes:
  - 0: successful compilation
  - 1: compilation error (unrecognized colors, malformed palette, invalid PNG)
  - 2: I/O error (missing files, write permissions)

## Example palette.json
```json
{
  "version": "palette-v0.1", 
  "tile_size": 16,
  "scan_order": "row-major",
  "opcodes": {
    "FF0000": "PUSHI",
    "0000FF": "ADD", 
    "FFFF00": "PRINT",
    "FFFFFF": "HALT"
  },
  "immediate_mode": "rgb-to-int",
  "tolerance": 5.0
}
```

## Example stdout (compilation summary)
```json
{
  "status": "success",
  "tiles_processed": 4,
  "instructions_generated": 4,
  "palette_hash": "a1b2c3d4e5f6...",
  "program_path": "program.json",
  "grid_size": {"width": 2, "height": 2},
  "unrecognized_colors": 0,
  "warnings": []
}
```

## Compilation Process
1. **Load and validate**: PNG format check, palette schema validation
2. **Grid extraction**: divide PNG into tile_size×tile_size tiles  
3. **Color decoding**: map tile colors to opcodes using palette + tolerance
4. **IR generation**: produce DVC JSON program in scan order
5. **Validation**: ensure output program is valid for DVC VM

## Error Examples
```json
// Unrecognized color
{
  "status": "error",
  "error": "Unrecognized color #123456 at tile (0,1)",
  "tiles_processed": 0,
  "program_path": null
}

// Malformed palette
{
  "status": "error", 
  "error": "Invalid palette: missing 'opcodes' field",
  "tiles_processed": 0,
  "program_path": null
}
```

## Determinism Requirements
- Identical PNG + palette + tolerance → identical JSON IR output
- Fixed tile scanning order and color matching algorithm
- Reproducible across different machines and PNG libraries