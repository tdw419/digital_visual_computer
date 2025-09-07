# Data Model — Color Language v0.1

This document defines the key entities and data structures for the color programming language, establishing the domain model for PNG-to-DVC compilation.

## Core Entities

### ColorPalette
**Purpose**: Maps RGB color values to DVC opcodes and defines encoding rules for the compilation process.

**Structure**:
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
  "tolerance": 5.0,
  "fiducials": {
    "808080": "ALIGN",
    "404040": "VERSION"
  }
}
```

**Attributes**:
- `version`: Schema version for palette format evolution
- `tile_size`: Pixel dimensions for tile grid (must divide image dimensions evenly)
- `scan_order`: Tile processing order ("row-major" only in v0.1)
- `opcodes`: RGB hex string → DVC opcode name mappings
- `immediate_mode`: How to extract immediate values from colors ("rgb-to-int" only)
- `tolerance`: ΔE color distance threshold for fuzzy color matching (0.0-100.0)
- `fiducials`: Reserved colors for alignment and version marking (optional)

**Validation Rules**:
- All hex colors must be 6 characters (RRGGBB format)
- Opcode names must match valid DVC instruction set
- `tile_size` must be positive integer, typically 8, 16, or 32
- `tolerance` must be non-negative float

---

### ColorProgram  
**Purpose**: Represents the PNG image file containing colored tiles that encode program instructions.

**Structure**: PNG file with metadata
- **Format**: PNG (RGB or RGBA)
- **Dimensions**: Must be divisible by palette.tile_size
- **Color Space**: sRGB, no ICC profiles
- **Size Limits**: 1024×1024 pixels maximum

**Grid Properties**:
- **Tile Count**: (width ÷ tile_size) × (height ÷ tile_size)
- **Tile Coordinates**: (row, col) where row=0 is top, col=0 is left
- **Scan Order**: Row-major traversal (left→right, top→bottom)

**Color Extraction**:
- **Sampling**: Use center pixel of each tile for color identification
- **RGB Conversion**: Extract (r, g, b) values from center pixel
- **Hex Format**: Convert to "RRGGBB" hex string for palette lookup

---

### TileGrid
**Purpose**: Intermediate representation of the PNG image divided into addressable tiles with position information.

**Structure**:
```python
{
  "dimensions": {"width": 4, "height": 3},  # in tiles
  "tile_size": 16,
  "tiles": [
    {"position": {"row": 0, "col": 0}, "color": "FF0000", "rgb": [255, 0, 0]},
    {"position": {"row": 0, "col": 1}, "color": "0000FF", "rgb": [0, 0, 255]},
    // ... more tiles in scan order
  ]
}
```

**Attributes**:
- `dimensions`: Grid size in tiles (not pixels)
- `tile_size`: Size of each tile in pixels
- `tiles`: Array of tile objects in scan order
  - `position`: Row/column coordinates of tile
  - `color`: RGB hex string extracted from tile center
  - `rgb`: Original [R, G, B] color components

---

### ColorIR
**Purpose**: Decoded intermediate representation linking tiles to DVC opcodes before final compilation.

**Structure**:
```python
{
  "palette_hash": "sha256:a1b2c3d4...",
  "compiler_version": "dvc-color-v0.1",
  "grid_size": {"width": 4, "height": 3},
  "instructions": [
    {"tile": {"row": 0, "col": 0}, "opcode": "PUSHI", "arg": "16711680", "source_color": "FF0000"},
    {"tile": {"row": 0, "col": 1}, "opcode": "ADD", "arg": null, "source_color": "0000FF"},
    // ... more instructions
  ],
  "unrecognized": [
    {"tile": {"row": 1, "col": 2}, "color": "123456", "message": "No palette match within tolerance"}
  ]
}
```

**Attributes**:
- `palette_hash`: SHA-256 of the palette.json for provenance
- `compiler_version`: Tool version that performed compilation
- `grid_size`: Dimensions of the tile grid
- `instructions`: Successfully decoded opcodes with position info
  - `tile`: Source position in the grid
  - `opcode`: DVC instruction name from palette
  - `arg`: Immediate value (for PUSHI) or null
  - `source_color`: Original hex color that produced this instruction
- `unrecognized`: Tiles that couldn't be mapped to opcodes

---

### CompileSummary
**Purpose**: Metadata and statistics about the compilation process for reporting and debugging.

**Structure**:
```json
{
  "status": "success",
  "tiles_processed": 12,
  "instructions_generated": 10,
  "palette_hash": "sha256:a1b2c3d4...",
  "program_path": "output.json",
  "grid_size": {"width": 4, "height": 3},
  "unrecognized_colors": [],
  "warnings": [
    "2 edge tiles ignored due to partial coverage"
  ],
  "compilation_time_ms": 45.2,
  "image_info": {
    "format": "PNG",
    "dimensions": {"width": 64, "height": 48},
    "color_mode": "RGB"
  }
}
```

**Attributes**:
- `status`: "success" | "error" | "partial"
- `tiles_processed`: Number of tiles scanned from image
- `instructions_generated`: Number of valid opcodes produced
- `palette_hash`: Hash of palette used for compilation
- `program_path`: Path to output DVC JSON file (null on error)
- `grid_size`: Tile grid dimensions
- `unrecognized_colors`: List of colors not found in palette
- `warnings`: Non-fatal issues encountered during compilation
- `compilation_time_ms`: Performance timing for optimization
- `image_info`: Original PNG metadata

## Data Flow

```
ColorProgram (PNG) + ColorPalette (JSON)
           ↓
      TileGrid (tiles with positions + colors)
           ↓
      ColorIR (tiles → opcodes + args)
           ↓
   DVC Program (JSON) + CompileSummary
```

## Integration Points

- **Trace Provenance**: ColorIR metadata flows into trace.meta.color_provenance
- **Bundle Assets**: Original PNG and palette preserved in .dvcf bundles
- **CLI Contracts**: CompileSummary provides stdout JSON for both compile/run commands
- **Error Reporting**: Unrecognized colors and warnings enable user debugging