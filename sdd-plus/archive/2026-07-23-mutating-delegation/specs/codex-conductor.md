# Capability (delta): codex-conductor

Capability: codex-conductor

Extends the conductor with MUTATING delegation: Codex writes real code in an isolated git worktree, gated by an applicability-first check, with no auto-merge. This is the one write-enabled path; the read-only paths are unchanged.

## ADDED Requirements

### R9 — Codex writes are isolated to a worktree, never the base branch
`mutate.py` SHALL run Codex with sandbox `workspace-write` confined to a dedicated worktree on a fresh `codex/…` branch created from `base`. The delegation SHALL NOT write to the Owner's branch or working tree, and this SHALL be the only conductor path that enables writes (the read-only `delegate()` lock is unchanged).

- **WHEN** a mutating task runs
- **THEN** Codex's changes appear only in the isolated worktree/branch; the base branch's HEAD is unadvanced and the main working tree is unmodified

### R10 — The gate is applicability-first; N/A is never a failure
Before pass/fail, the merge gate SHALL decide whether it applies. A docs/config-only change makes the test gate N/A (a clean pass). A code/behavior change requires green tests (a red or not-run result is a hard block). N/A SHALL be a distinct outcome from FAIL.

- **WHEN** the change touches only docs/config
- **THEN** the gate verdict is `n/a` with `clears: true` — not a failure

- **WHEN** the change touches code and tests are red or were not run
- **THEN** the gate verdict is `red`/`blocked` with `clears: false`

- **WHEN** the change touches code and tests pass
- **THEN** the gate verdict is `green` with `clears: true`

### R11 — No auto-merge; structured verdict for review
`mutate.py` SHALL NEVER merge. It SHALL return a structured result (`worktree, branch, diff, files, tests, gate, clears_gate, merged: false, note`) for Claude to review and merge deliberately. Clearing the deterministic gate is necessary, not sufficient — Claude's diff review is still required. Every outcome SHALL be structured (no bare traceback).

- **WHEN** a mutating delegation completes
- **THEN** the result reports `merged: false` and carries the diff + gate verdict; the worktree is kept when there is something to review and cleaned up on empty/failed delegation

### R12 — Cleanup is blast-radius-bounded
Worktree cleanup SHALL remove only the temp worktree and a branch whose name begins with `codex/`; it SHALL never delete any other branch.

- **WHEN** cleanup is asked to delete a non-`codex/` branch
- **THEN** that branch is left intact
