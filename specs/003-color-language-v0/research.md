# Research — Color Language v0.1 (PNG + Palette → DVC JSON IR)

This document resolves technical design questions for visual programming using colors, establishing canonical choices for deterministic compilation from PNG images to DVC executable code.

## Decisions

**Color Encoding Format**: Exact RGB hex matching with tolerance bands
- Rationale: Precise, deterministic color identification; tolerance handles anti-aliasing/compression artifacts
- Primary matching: exact RGB hex values (e.g., #FF0000 → "PUSHI") 
- Fallback: configurable ΔE color distance threshold (default: 5.0) for near-matches
- Encoding: palette.json maps hex strings to opcodes/roles

**Tile Geometry**: Fixed 16×16 pixel tiles, row-major scanning
- Rationale: Balance between visual clarity and compact encoding; matches common pixel art conventions
- Grid: divide PNG width/height by 16, round down; partial tiles ignored
- Scan order: left→right, top→bottom (reading order)
- Position encoding: (row, col) coordinates preserved in ColorIR for debugging

**Immediate Value Encoding**: RGB components as integer  
- Format: RGB(r,g,b) → integer value = r + (g << 8) + (b << 16)
- Range: 0-16777215 (24-bit color space)
- Usage: PUSHI instructions get arg from color's numeric interpretation
- Example: RGB(42, 0, 0) → PUSHI "42", RGB(255, 255, 255) → PUSHI "16777215"

**Palette Schema v0.1**: JSON with opcodes, immediates, and metadata
```json
{
  "version": "palette-v0.1",
  "tile_size": 16,
  "scan_order": "row-major",
  "opcodes": {
    "000000": "NOP",     // black = no-operation
    "FFFFFF": "HALT",    // white = halt
    "FF0000": "PUSHI",   // red = push immediate (value from RGB)
    "00FF00": "POP",     // green = pop stack
    "0000FF": "ADD",     // blue = addition
    "FFFF00": "SUB",     // yellow = subtraction  
    "FF00FF": "MUL",     // magenta = multiply
    "00FFFF": "DIV",     // cyan = divide
    "FFA500": "PRINT"    // orange = print/output
  },
  "immediate_mode": "rgb-to-int",
  "tolerance": 5.0,
  "fiducials": {
    "808080": "ALIGN",   // gray = alignment marker (reserved)
    "404040": "VERSION"  // dark gray = version marker (reserved)
  }
}
```

**PNG Loading Requirements**: Strict format constraints for determinism
- Format: PNG only (no JPEG, GIF, WebP); RGB or RGBA supported
- Color management: disable ICC profiles and gamma correction
- Alpha handling: treat RGBA as RGB (ignore alpha channel for v0.1)
- Size limits: max 1024×1024 pixels (prevents memory issues)
- Loader: use deterministic PNG library with locked parameters

**Compilation Pipeline**: PNG → ColorIR → DVC JSON IR
1. **Load Phase**: PNG + palette.json → validated inputs
2. **Decode Phase**: tile-by-tile color extraction → opcode identification
3. **Lower Phase**: ColorIR (tiles + positions + ops) → DVC Program JSON
4. **Validate Phase**: ensure output Program is well-formed for existing VM

**Error Handling**: Fail-fast with detailed position information
- Unknown colors: report tile position and RGB value
- Malformed palette: validate schema before processing
- Invalid PNG: check format, size, color mode before decode
- Partial tiles: warn but continue (ignore incomplete edge tiles)

## Alternatives Considered

**HSV/LAB Color Spaces**: Rejected for v0.1 simplicity; RGB is universal and deterministic
- May revisit for v0.2 with perceptual color matching

**Variable Tile Sizes**: Rejected; fixed 16×16 provides predictable grid and performance
- Could add as palette.tile_size configuration in future versions

**Floating-Point Immediates**: Rejected for determinism; DVC VM uses integer arithmetic only
- Future tensor operations may need quantized fixed-point encoding

**Spatial Control Flow**: Rejected for v0.1; linear execution matches DVC VM design
- v0.2 could add arrow tiles, jump opcodes for non-linear programs

**Multiple Palette Inheritance**: Rejected for complexity; single palette.json per program
- Bundle format can include palette provenance for auditability

## Format Examples

**Minimal 2×2 Program** (32×32 PNG):
```
[Red]   [Blue]      // PUSHI <red-value>, ADD
[Yellow][White]     // PRINT, HALT
```

**Corresponding palette.json**:
```json
{"opcodes": {"FF0000": "PUSHI", "0000FF": "ADD", "FFFF00": "PRINT", "FFFFFF": "HALT"}}
```

**Expected DVC JSON IR**:
```json
[
  {"op": "PUSHI", "arg": "16711680"},
  {"op": "ADD"},
  {"op": "PRINT"}, 
  {"op": "HALT"}
]
```

## Integration Points

**Bundle Format Extension**: Add assets/program.png, assets/palette.json to .dvcf
**CLI Extension**: dvc color-compile, dvc color-run commands reuse existing VM/verify
**Trace Provenance**: Include palette hash and compiler version in trace.meta for reproducibility
**Deterministic Compilation**: --deterministic-meta flag applies to color programs for byte-identical traces

## Open Questions (to resolve in planning)

- Default immediate encoding for non-PUSHI opcodes (currently RGB→int always applied)
- Fiducial placement rules and semantic meaning for alignment/versioning
- Color tolerance tuning methodology (perceptual vs. Euclidean distance)
- Integration with CSV pixel programs from earlier research