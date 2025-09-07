# Implementation Plan: DVC v0.1 Core - Deterministic VM with Hash-Chained Execution Traces

**Branch**: `002-dvc-v0-1` | **Date**: 2025-01-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-dvc-v0-1/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Build a deterministic Virtual Machine (VM) that executes stack-based programs with complete execution tracing and cryptographic hash chaining. Primary goal is creating tamper-evident computational artifacts where identical inputs produce identical execution traces across different machines and times.

## Technical Context
**Language/Version**: Python 3.11+ (deterministic execution, rich ecosystem)  
**Primary Dependencies**: hashlib (hashing), dataclasses (structured data), typing (type safety), json (trace serialization)  
**Storage**: File-based (JSON traces, CSV programs, no database needed)  
**Testing**: pytest (test-first development, fixtures, parametrized tests)  
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows)
**Project Type**: Single CLI project with library core  
**Performance Goals**: 10,000 execution steps/second, sub-100ms verification  
**Constraints**: Deterministic execution, tamper-evident traces, byte-identical results  
**Scale/Scope**: Programs up to 10,000 instructions, traces up to 1M steps

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 2 (dvc_core library, dvc CLI)
- Using framework directly? (direct Python stdlib, no web frameworks)
- Single data model? (unified VM state, trace format)
- Avoiding patterns? (direct implementation, no complex abstractions)

**Architecture**:
- EVERY feature as library? (dvc_core library + CLI wrapper)
- Libraries listed: dvc_core (VM engine + trace verification)
- CLI per library: `dvc run`, `dvc verify`, `dvc --help --version --format json`
- Library docs: llms.txt format planned for Claude Code integration

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? (tests must fail before implementation)
- Git commits show tests before implementation? (contract tests first)
- Order: Contract→Integration→E2E→Unit strictly followed
- Real dependencies used? (actual file system, no mocks for I/O)
- Integration tests for: VM execution, trace verification, CLI commands
- FORBIDDEN: Implementation before test, skipping RED phase

**Observability**:
- Structured logging included? (execution steps, verification progress)
- Frontend logs → backend? (N/A - CLI only)
- Error context sufficient? (stack traces, VM state on errors)

**Versioning**:
- Version number assigned? (0.1.0)
- BUILD increments on every change? (patch version per commit)
- Breaking changes handled? (trace format versioning, migration tests)

## Project Structure

### Documentation (this feature)
```
specs/002-dvc-v0-1/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── dvc_core/           # Core VM library
│   ├── __init__.py
│   ├── vm.py           # Virtual machine implementation
│   ├── opcodes.py      # Instruction definitions
│   ├── trace.py        # Execution tracing
│   ├── hash_chain.py   # Cryptographic chaining
│   └── verifier.py     # Trace verification
├── dvc_cli/            # Command-line interface
│   ├── __init__.py
│   ├── commands.py     # CLI command handlers
│   └── main.py         # Entry point
└── lib/                # Utilities
    ├── __init__.py
    ├── program_loader.py # CSV program parsing
    └── trace_serializer.py # JSON trace I/O

tests/
├── contract/           # CLI contract tests
│   ├── test_run_command.py
│   ├── test_verify_command.py
│   └── fixtures/       # Golden test files
├── integration/        # End-to-end tests
│   ├── test_vm_execution.py
│   ├── test_trace_verification.py
│   └── test_determinism.py
└── unit/               # Component tests
    ├── test_vm.py
    ├── test_opcodes.py
    ├── test_trace.py
    └── test_hash_chain.py
```

**Structure Decision**: Option 1 (Single project) - CLI tool with library core, no web/mobile components

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - Default step limit value for infinite loop protection
   - Specific CSV program encoding format from research docs
   - JSON trace serialization schema design
   - Hash algorithm choice (SHA-256, Blake3, etc.)
   - Integer size/overflow handling behavior

2. **Generate and dispatch research agents**:
   ```
   Task: "Research optimal step limit for VM execution safety"
   Task: "Analyze CSV pixel program format from DVC research docs"
   Task: "Design JSON trace schema for hash-chained execution steps"
   Task: "Compare hash algorithms for deterministic VM traces"
   Task: "Research integer handling in stack-based VMs"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Program, Opcode, TraceStep, ExecutionTrace, VMState, HashChain
   - Field definitions, validation rules, state transitions
   - Serialization formats and schemas

2. **Generate CLI contracts** from functional requirements:
   - `dvc run --program file.csv --trace output.json --limit 10000`
   - `dvc verify --trace file.json --strict`
   - `dvc --help --version --format json`
   - Output contract schemas to `/contracts/`

3. **Generate contract tests** from contracts:
   - test_cli_run_contract.py (input/output validation)
   - test_cli_verify_contract.py (verification behavior)
   - Tests must fail (no CLI implementation yet)

4. **Extract test scenarios** from user stories:
   - Simple arithmetic execution test
   - Cross-machine determinism test
   - Trace verification test
   - Error handling scenarios

5. **Update CLAUDE.md incrementally**:
   - Add DVC VM concepts and terminology
   - Include trace format and CLI patterns
   - Preserve existing content between markers

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, CLAUDE.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/spec-kit/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each CLI contract → contract test task [P]
- Each entity (VM, Trace, etc.) → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Contract tests → Integration tests → Unit tests → Implementation
- Dependency order: Core models → VM engine → CLI → Verification
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 20-25 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*No constitutional violations identified - simple CLI + library design*

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS
- [ ] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/spec-kit/memory/constitution.md`*