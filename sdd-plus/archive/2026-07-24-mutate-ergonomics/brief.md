# Brief

## Change

mutate-ergonomics

## User Need

Field report #2, from weeks of daily use on a real Next.js/Supabase repo. `mutate` shipped in 0.11.0 with a cost meter, `--files` scoping, and a diff-shape advisory — and the operator's first real use surfaced that the meter reads zero, the scoping lever is capped below real files, and a timed-out sweep throws its work away.

## Problem

Five concrete defects, all measured on a real repo:

1. **The cost meter I designated authoritative reads `0`.** A 181,184-token task moved the weekly gauge by less than 1% — below its integer resolution — so `fuel_used_percent` rounds to `0`, which reads as "free." Same absence-of-evidence-as-reassurance failure as the boolean-gauge bug. And the reporter's reframe matters: input cost is a **near-fixed repo-ingestion floor** (~180k here), not driven by task size — so tokens, not the coarse gauge, are what discriminate per task.
2. **`--files` is capped at 64KB/file** — below `tools.ts` at 90,614 bytes, the file they edit most — and **asymmetric** with `--diff`'s 256KB. Since ingestion is the dominant cost, scoping is the *only* lever on it, and it fails exactly where it's needed.
3. **A timed-out delegation discards its partial work.** `mutate()` cleans up the worktree on any non-ok delegation, so a sweep killed at the 600s timeout loses its 100 insertions.
4. **An externally-killed run orphans the worktree + branch** with no cleanup path.
5. **600s is too short for a mechanical sweep** over a large file, and there's no operator lever to raise it.

## Scope

In scope: fix all five in `mutate.py`. Below-resolution fuel → `null` + `fuel_resolution`, tokens as the primary signal, clearer field names. Unify `--files` caps with `--diff`. Salvage partial work on timeout (keep tree, flag `partial`, never clear the gate). `--timeout` lever + raised default. `--gc` for orphaned `codex/` worktrees.

Out of scope: the archive-inversion / lifecycle work (§4 of the report — the flagship next packet); the STANDARD ceremony collapse (rides with it); any change to merge behavior or the gate's verdict logic.

## Acceptance Criteria

- [ ] A sub-resolution task reports `fuel_used_percent: null` with a reason, never `0`; a genuine no-op (no tokens) is not falsely flagged sub-resolution.
- [ ] `--files` and `--diff` share one set of caps; a 90KB file is scopable.
- [ ] A timed-out run with changes keeps its worktree, is flagged `partial`, and does not clear the gate; a timed-out run that wrote nothing is cleaned up.
- [ ] `--timeout` is honored within a clamped range; the default is raised.
- [ ] `--gc` removes only empty `codex/` worktrees, keeps ones holding work, and never touches a non-codex worktree.

## Impact Areas

- Backend: `scripts/conductor/mutate.py` only.
- API: `mutate()` gains `timeout=`; `cost` fields renamed/extended; result gains `partial`; new `--timeout`/`--gc`/`--dry-run` CLI and `gc_worktrees()`.
- AI/model behavior: unchanged (delegation prompt only widens the inline cap).
- Documentation: operator guide's mutating-delegation paragraph.
- Operations/security: `--gc` deletes worktrees — blast-radius-bounded to `codex/` and never removes one holding uncommitted work.

## Open Questions

- The mutate timeout can't scale on a fixed payload the way `--diff` does (Codex reads the whole tree), so this ships a raised default + an operator lever rather than an automatic scale. If sweeps routinely trip it, revisit with a size heuristic.
