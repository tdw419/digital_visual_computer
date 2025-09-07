# Research — DVC v0.1 Core (Deterministic VM + Hash-Chained Trace)

This document resolves technical unknowns for a deterministic, auditable VM and establishes canonical choices for v0.1 to ensure cross-machine reproducibility.

## Decisions

- Integer model: Arbitrary-precision signed integers
  - Rationale: Avoids overflow ambiguity across platforms; Python bigints are deterministic.
  - Trace encoding: Integers serialized as decimal strings to avoid JSON number pitfalls.

- Division semantics: Truncate toward zero (C/Java style)
  - Example: 5/2 → 2, -5/2 → -2. Division by zero is a fault.

- Step limit: Default 10,000 (configurable)
  - Rationale: Prevent non-termination; recorded in metadata.

- Program format (v0.1 canonical): JSON IR
  - Shape: [{"op": "PUSHI", "arg": "2"}, {"op": "PUSHI", "arg": "3"}, {"op": "ADD"}, {"op": "PRINT"}, {"op": "HALT"}]
  - Rationale: Deterministic, lossless, easy to validate. Pixel/CSV encodings are separate features that compile to this IR.

- Opcode set (v0.1): NOP, HALT, PUSHI, POP, ADD, SUB, MUL, DIV, PRINT
  - Deterministic semantics defined below; expansions come in later specs.

- Hash function: SHA-256
  - Rationale: Ubiquitous, well-understood, sufficient for v0.1

- Hash-chain construction:
  - Canonicalize step object to JSON with sorted keys, no whitespace, UTF-8 bytes
  - step_hash_i = SHA256(step_json_i || prev_hash_hex_i-1)
  - prev_hash_hex_0 = 64 zero chars ("0"*64)
  - final_root = step_hash_last (hex)

- Trace schema (v0.1): Single JSON object
  - { meta, steps[] }
  - meta: { version, step_limit, halted, faulted, outputs, final_root, started_at, finished_at }
  - steps[i]: { index, ip, op, arg?, stack_before[], stack_after[], output?, note?, fault?, step_hash }

- Encoding and locale:
  - UTF-8 throughout; no locale dependence; newlines "\n" only.

- Determinism controls:
  - No non-deterministic ops in v0.1 (no time, rand, I/O)
  - Stable sorting, stable JSON canonicalization, stable integer/text handling

## Alternatives considered

- Fixed-width integers (e.g., 64-bit two’s complement)
  - Rejected for v0.1: introduces overflow behavior and byte-ordering considerations; may be revisited for perf parity.

- BLAKE3/Keccak instead of SHA-256
  - Rejected for v0.1 simplicity/ubiquity; may add as selectable algorithms later.

- Streaming/NDJSON traces
  - Keep v0.1 simple (single JSON). Add streaming verification in later feature.

## Open Questions (track to resolve if needed)
- Canonical field names locked? (op vs opcode; arg vs imm)
- Formal JSON schema file for meta/steps (v0.1 optional vs required)

## Deterministic Semantics (opcode summary)
- PUSHI x: push integer x
- POP: pop top (fault if stack empty)
- ADD/SUB/MUL: pop b, pop a, push a±b / a*b (fault if underflow)
- DIV: pop b, pop a, fault if b==0, else push trunc(a/b)
- PRINT: pop top, append to outputs, continue
- NOP: no-op
- HALT: stop; record halted=true

