# Contract — dvc run (v0.1)

Purpose: Execute a canonical JSON-IR program and emit a canonical JSON trace with a final root.

## Invocation
```
dvc run --program <program.json> --trace <out.json> [--limit <n>] [--format json]
```

## Inputs
- program.json: JSON array of instruction objects (see Program IR in research/data-model)
- --limit: optional step cap; default 10000

## Outputs
- Writes canonical trace to <out.json>
- Stdout (when --format json): summary JSON: { "status", "steps", "outputs", "final_root", "trace_path" }
- Exit codes:
  - 0: success (halted or clean completion)
  - 2: fault (e.g., divide by zero, stack underflow) — trace still written with fault info
  - 1: other errors (I/O, malformed program)

## Example program.json
```
[
  {"op":"PUSHI","arg":"2"},
  {"op":"PUSHI","arg":"3"},
  {"op":"ADD"},
  {"op":"PRINT"},
  {"op":"HALT"}
]
```

## Example stdout (summary)
```
{
  "status": "halted",
  "steps": 5,
  "outputs": ["5"],
  "final_root": "<64-hex>",
  "trace_path": "out/trace.json"
}
```

## Canonicalization requirements
- Trace JSON written with sorted keys and no insignificant whitespace
- Integers represented as decimal strings
- UTF-8 file encoding, newline "\n"

