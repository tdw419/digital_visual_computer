# Contract — dvc verify (v0.1)

Purpose: Verify the integrity of a DVC execution trace through full hash chain validation and metadata consistency checks.

## Verification Process
**Default behavior**: Recomputes the entire hash chain from scratch, validates metadata consistency with steps, and detects any tampering or corruption.

**Enhanced validation**:
- Recomputes SHA-256 hash for each step using canonical JSON
- Validates hash chain links (each step's hash depends on previous hash)
- Checks metadata.outputs matches actual outputs from PRINT steps
- Verifies final_root matches last step's hash
- Detects any data tampering or fabricated hashes

## Invocation
```
dvc verify --trace <trace.json> [--strict] [--replay] [--format json]
```

## Inputs
- trace.json: Canonical trace per v0.1 schema (must have valid hash chain)
- --strict: Enable additional consistency checks (reserved for future)
- --replay: Enable semantic replay mode (reserved for future)

## Outputs
- Stdout (when --format json): { "status", "valid", "final_root", "steps", "faulted", "halted", "trace_path", "error"? }
- Exit codes:
  - 0: valid trace
  - 1: invalid trace (hash mismatch, tampering detected, or format error)

## Example stdout
```
{
  "valid": true,
  "final_root": "<64-hex>",
  "steps": 5,
  "faulted": false,
  "halted": true
}
```

