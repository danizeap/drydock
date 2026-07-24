# Capability (delta): codex-enforcement-bridge

Capability: codex-enforcement-bridge

Corrects the mutating-delegation cost signal, unifies the scoping caps with review, and makes a timed-out run recoverable — all from field report #2.

## ADDED Requirements

### R5 — Cost is reported at the resolution it was actually measured
The per-task cost SHALL treat **token counts as the primary signal** (they have resolution at task scale) and the **fuel-gauge delta as a coarse window-drain signal**. When the gauge did not move measurably but tokens were spent, `fuel_used_percent` SHALL be `null` with a stated reason — it SHALL NOT report `0`, which reads as "free." A genuine no-op (no tokens spent) is not a sub-resolution cost. Fuel fields SHALL be named so their polarity (used, not remaining) is unambiguous.

- **WHEN** a task spends tokens but moves the weekly gauge by less than its resolution
- **THEN** `fuel_used_percent` is `null` and `fuel_resolution` says "below gauge resolution" — never `0`

- **WHEN** the quota window resets mid-run (after-reading below before-reading)
- **THEN** `fuel_used_percent` is `null` and `fuel_resolution` says "window reset"

- **WHEN** the run spent no tokens and the gauge did not move
- **THEN** this is a true no-op, not flagged as sub-resolution

### R6 — Scoping caps do not fall below real files, and do not drift from review
The `--files` inline caps (per-file and total) SHALL equal the `--diff` review caps, so a file that is reviewable is also scopable and the two paths cannot diverge.

- **WHEN** a named target is up to the shared per-file cap (e.g. a 90KB source file)
- **THEN** it is inlined, not refused

- **WHEN** the review caps change
- **THEN** the scoping caps change with them (one source of truth)

### R7 — A timed-out delegation is recoverable, never green
On delegation timeout, any work already written to the worktree SHALL be preserved: the worktree is kept, the result is flagged `partial`, and a partial run SHALL NOT clear the gate regardless of test outcome, because incomplete work is not verified work. A timed-out run that produced no changes SHALL be cleaned up. The delegation timeout SHALL be operator-adjustable within a clamped range.

- **WHEN** a delegation times out after Codex wrote changes
- **THEN** the worktree is kept, `partial` is true, `clears_gate` is false, and the note says INCOMPLETE

- **WHEN** a delegation times out having written nothing
- **THEN** the empty worktree is cleaned up

- **WHEN** the operator raises `--timeout`
- **THEN** it is honored within a clamped range (a sweep over a large file gets the time it needs)

### R8 — Orphaned worktrees are recoverable, blast-radius-bounded
A garbage-collection path SHALL remove orphaned `codex/` worktrees that hold no salvageable work, SHALL keep and report ones that hold work — **uncommitted changes OR commits unique to the codex branch** — and SHALL never touch a non-`codex/` worktree. Where the presence of work cannot be determined, it SHALL fail safe and keep.

- **WHEN** an empty `codex/` worktree is orphaned (e.g. by an external kill)
- **THEN** `--gc` removes it

- **WHEN** a `codex/` worktree holds uncommitted work
- **THEN** `--gc` keeps it and reports it — the salvage is not auto-destroyed

- **WHEN** a `codex/` worktree holds committed work not present on any non-codex branch
- **THEN** `--gc` keeps it — "no uncommitted changes" is not "no work"

- **WHEN** the work-check errors or is indeterminate
- **THEN** `--gc` keeps the worktree rather than risk destroying salvage

- **WHEN** a non-`codex/` worktree exists
- **THEN** `--gc` never touches it, and `--dry-run` removes nothing
