# Capability (delta): codex-conductor

Capability: codex-conductor

Extends the conductor with the endurance substrate: a HANDOFF.md relay for leadership transfer between agents, plus fuel-aware fleet advice.

## ADDED Requirements

### R17 — Deterministic, read-only handoff state
`handoff.py::gather_state()` SHALL capture, without mutating the repo, the branch, HEAD, active change packets, open `codex/` worktrees, and the executor `fleet_status()`. Git/read failures SHALL degrade to benign values, never a traceback.

- **WHEN** `gather_state()` runs in a project
- **THEN** it returns the branch, HEAD, active packets, open codex worktrees, and the fleet — and makes no changes

### R18 — HANDOFF.md is a fixed-shape relay, re-verified on the way in
`write_handoff()` SHALL render a fixed-shape `HANDOFF.md` (where-we-are / fleet fuel / next step / notes) where only the next step + notes are human-supplied; `read_handoff()` returns it or None. The `/drydock:handoff` command SHALL instruct the incoming leader to reconstruct from live repo reality — HANDOFF.md never overrides `git`/`sdd.py status`.

- **WHEN** a leader writes a handoff
- **THEN** HANDOFF.md carries the deterministic state + the one-line next step; the incoming leader re-verifies against reality before acting

### R19 — Fuel-aware fleet advice; Claude is human-tracked
`fleet_recommendation()` SHALL list each usable tank's fuel/reset, flag a low tank (`<15%`), prefer spending the tank closest to its reset (protect the far one), and always note Claude as human-tracked (its quota is not machine-readable).

- **WHEN** two tanks are usable with different reset horizons
- **THEN** the advice prefers spending the nearer-reset tank and protecting the other; Claude is noted as human-tracked
