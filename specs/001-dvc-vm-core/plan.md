# DVC v0.1 Core Implementation Plan

**Technical Context**
- VM: Stack-based deterministic execution with step-by-step trace and hash chaining
- Visual ritual system: 4-pane SVG viewer showing palette/opcodes, disassembly, IR/dataflow, outputs/state
- Packaging: Content-addressed `.dvcf` bundles containing program, trace, visual assets, proofs
- Verification: Semantic replay + hash validation; streaming/partial verification support in roadmap
- Pixel-program system: CSV encoding with blue channel symbols (255 = evaluate now)
- Color ISA mapping: NOP/HALT/PUSHI/ADD/SUB/MUL/DIV/PRINT operations to tile grid geometry

**Data Models**
- `TraceStep`: Execution step with opcode, inputs, outputs, state
- `Opcode`: Enum representing all defined operations with color mappings
- `Bundle`: Content-addressed package with manifest and verification proofs
- `Attestation`: Multi-sig proof of execution integrity

**Contracts**
```json
{
  "dvc run --frame path.png --trace out.json": {
    "stdin": null,
    "stdout": "{ \"summary\": string, \"hash\": hex }",
    "exit_code": 0,
    "outputs": [ "out.json" ]
  },
  "dvc verify --bundle run.dvcf": {
    "stdin": null,
    "stdout": "JSON validation output",
    "exit_code": 0
  }
}
```

**Implementation Priorities**
1. Core VM implementation with hash-chained trace system
2. Pixel-program CSV decoder and validator
3. Basic `.dvcf` packaging with manifest
4. Initial SVG viewer integration
5. Verification contract implementation

**Constitutional Alignment**
- ✅ Simplification: All components use minimal dependencies and clear interfaces
- ✅ Test-first: Every component must pass tests before implementation
- ✅ Observability: Full trace output with deterministic hash chaining
