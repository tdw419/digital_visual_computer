# Start-Over Protocol (Greenfield Resets)

Purpose: Allow the team/AI to intentionally restart a feature or subsystem when a clearly better approach emerges, while preserving lineage, tests, and auditability.

## When to Start Over
- Simpler architecture exists that removes significant complexity or risk.
- Performance or determinism constraints cannot be met by refactoring.
- Spec/contract changes make current implementation a poor fit.
- Repeated regressions or fragile integrations indicate structural issues.

## Guardrails (make the decision explicit)
- Write a short REWRITE note with: problem statement, new approach, acceptance criteria, risks, rollback plan.
- Tag the current branch as a lineage checkpoint.
- Identify tests/contracts to carry forward. Keep golden fixtures.

## Procedure
1. Freeze current work
   - Tag: `rewrite/<date>-<reason>`
   - Open REWRITE note in the repo (see below)
2. Create a greenfield feature
   - Use `spec-kit/scripts/start-over.sh "<short description>"`
   - This creates a new feature branch `R###-...` and seeds `specs/R###-.../REWRITE.md`
3. Carry forward contracts & tests
   - Copy/port CLI contracts and integration tests first (they define truth)
   - Mark explicit drifts (allowed changes) in the REWRITE note
4. Implement fresh
   - Follow spec-kit TDD gates; keep design simple; remove prior abstractions
5. Deprecate prior track
   - Document migration or co-existence plan
   - Link old → new in `docs/research/RESTARTS.md`

## Naming
- Branch: `R###-rewrite-<topic>` (e.g., `R001-rewrite-trace`)
- Specs dir: `specs/R###-rewrite-<topic>/`
- Tag prior state: `rewrite/<date>-<topic>`

## Lineage & Audit
- Treat restarts as lineage events (Hall of Drift)
- Keep REWRITE note + links to tags/branches
- Preserve golden data and final_root hashes from prior track for comparison

---

Minimal is better: restart only when there’s a material win; otherwise iterate.
