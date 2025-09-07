# Implementation Plan — Color Language v0.1

**Feature Branch**: `003-color-language-v0`  
**Status**: Planning  
**Methodology**: TDD (Test-Driven Development)

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PNG Image     │────│  Color Compiler  │────│   DVC JSON IR   │
│   + Palette     │    │    Pipeline      │    │   + Summary     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   DVC VM Core    │
                       │  (existing v0.1) │
                       └──────────────────┘
```

## Implementation Phases

### Phase 1: Core Data Structures
**TDD Cycle**: RED → GREEN → Refactor

**Files to Create**:
- `src/color_lang/__init__.py` - Package initialization
- `src/color_lang/palette.py` - ColorPalette data model with validation
- `src/color_lang/image.py` - PNG loading and TileGrid extraction
- `src/color_lang/compiler.py` - ColorIR generation and DVC JSON output

**Test Files**:
- `tests/color_lang/test_palette.py` - Palette validation and color matching
- `tests/color_lang/test_image.py` - PNG processing and tile extraction  
- `tests/color_lang/test_compiler.py` - Color→opcode compilation

### Phase 2: CLI Integration
**Dependencies**: Phase 1 complete

**Files to Modify**:
- `src/dvc_cli/main.py` - Add color-compile and color-run commands
- `src/dvc_cli/color_commands.py` - New module for color CLI handlers

**Test Files**:
- `tests/cli/test_color_commands.py` - CLI contract tests
- `tests/integration/test_color_e2e.py` - End-to-end color workflow

### Phase 3: Contract Validation
**Dependencies**: Phase 2 complete

**Test Files**:
- `tests/contract/test_color_compile.py` - Validate color-compile contract
- `tests/contract/test_color_run.py` - Validate color-run contract

## TDD Workflow

### RED Phase: Write Failing Tests
1. Create test fixtures (sample PNG images + palettes)
2. Write contract tests that call CLI commands
3. Write unit tests for each data model
4. Verify all tests fail with clear error messages

### GREEN Phase: Minimal Implementation
1. Implement ColorPalette loading and validation
2. Implement PNG tile extraction with center pixel sampling
3. Implement color-to-opcode mapping with tolerance
4. Implement CLI command handlers
5. Verify all tests pass

### REFACTOR Phase: Improve Design
1. Extract common patterns and utilities
2. Optimize PNG processing performance
3. Enhance error messages and validation
4. Add comprehensive logging

## File Structure

```
src/color_lang/
├── __init__.py          # Package exports
├── palette.py           # ColorPalette model + validation
├── image.py            # PNG loading + TileGrid extraction
├── compiler.py         # ColorIR + DVC JSON generation
└── exceptions.py       # Color-specific error types

src/dvc_cli/
├── main.py             # Updated with color commands
└── color_commands.py   # color-compile, color-run handlers

tests/color_lang/
├── test_palette.py     # Palette parsing + color matching
├── test_image.py       # PNG processing + tile grid
├── test_compiler.py    # Compilation pipeline
└── fixtures/           # Test images + palettes
    ├── simple_2x2.png
    ├── simple_2x2_palette.json
    ├── invalid_colors.png
    └── malformed_palette.json

tests/contract/
├── test_color_compile.py  # CLI contract validation
└── test_color_run.py     # CLI contract validation

tests/integration/
└── test_color_e2e.py     # Full workflow tests
```

## Dependencies

### Required Libraries
- **Pillow (PIL)**: PNG image processing
  ```bash
  pip install Pillow==10.0.0
  ```

### Existing Dependencies
- `src.dvc_core.vm` - VM execution engine
- `src.dvc_core.verifier` - Trace verification
- `src.dvc_cli.main` - CLI framework

## Success Criteria

### Functional Tests Pass
- [ ] All contract tests validate CLI behavior matches specs
- [ ] Color compilation produces valid DVC JSON programs
- [ ] Color programs execute identically to hand-written JSON
- [ ] Deterministic compilation (same PNG+palette → same output)

### Integration Tests Pass  
- [ ] color-compile → dvc run → dvc verify workflow
- [ ] color-run → dvc verify workflow
- [ ] Error handling for invalid colors, bad PNG files
- [ ] Trace provenance includes color metadata

### Performance Benchmarks
- [ ] Compile 64×64 image in <100ms
- [ ] Support up to 1024×1024 images
- [ ] Memory usage stays under 50MB for largest images

## Risk Mitigation

### PNG Library Determinism
- **Risk**: Different PIL versions produce different pixel values
- **Mitigation**: Lock Pillow version, disable color management

### Color Matching Accuracy
- **Risk**: Anti-aliasing causes color drift
- **Mitigation**: Use center pixel sampling + configurable tolerance

### Test Image Consistency
- **Risk**: Image editors introduce artifacts
- **Mitigation**: Generate test PNGs programmatically in test setup

## Next Steps

1. **Create test fixtures**: Generate minimal PNG programs + palettes
2. **Write failing contract tests**: Validate CLI commands don't exist yet
3. **Implement data models**: Start with ColorPalette validation
4. **Follow TDD cycle**: RED → GREEN → Refactor for each component