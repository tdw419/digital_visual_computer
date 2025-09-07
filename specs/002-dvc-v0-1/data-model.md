# Data Model — DVC v0.1 Core

## Entities

- Program
  - description: Ordered list of instruction objects (canonical IR)
  - fields:
    - instructions: Instruction[]

- Instruction
  - fields:
    - op: string (enum: NOP, HALT, PUSHI, POP, ADD, SUB, MUL, DIV, PRINT)
    - arg: string (decimal integer) — only for PUSHI

- VMState
  - fields:
    - ip: integer (0-based instruction pointer)
    - stack: string[] (decimal integers, top at end)
    - outputs: string[] (decimal integers)
    - status: string (running|halted|faulted)

- TraceStep
  - fields:
    - index: integer (0-based step index)
    - ip: integer (ip before executing step)
    - op: string
    - arg: string (optional)
    - stack_before: string[]
    - stack_after: string[]
    - output: string (optional, value emitted by PRINT)
    - note: string (optional)
    - fault: string (optional, error message)
    - step_hash: string (hex)

- Trace
  - fields:
    - meta: TraceMeta
    - steps: TraceStep[]

- TraceMeta
  - fields:
    - version: string (e.g., "dvc-trace-0.1")
    - step_limit: integer
    - halted: boolean
    - faulted: boolean
    - outputs: string[]
    - final_root: string (hex)
    - started_at: string (ISO8601 UTC)
    - finished_at: string (ISO8601 UTC)

## Invariants
- steps[i].stack_after equals steps[i+1].stack_before
- meta.final_root equals steps[last].step_hash when steps non-empty
- Deterministic: same Program + initial state + step_limit ⇒ identical Trace

