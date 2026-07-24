# Plan

## Change

mutate-ergonomics

## Approach

1. **`summarize_cost`** — add `spent` (any tokens present). When before==after but tokens were spent, `fuel_used_percent = null` and `fuel_resolution = "below gauge resolution"`; a reset (after<before) → `null` + "window reset". A genuine no-op (no tokens, zero delta) stays `0`. Rename `fuel_before/after_percent` → `fuel_used_before/after_percent` (they're *used* percentages, opposite the gauge's `remaining_percent` — the reporter's confusion). Flip the note: tokens are the per-task cost, fuel delta is the coarse window-drain signal.
2. **Caps (N1)** — `MAX_INLINE_FILE_BYTES = rv.MAX_FILE_BYTES`, `MAX_INLINE_BYTES = rv.MAX_TOTAL_BYTES`. Import review's constants directly so the two paths can never drift asymmetric again.
3. **Timeout + partial (N2/N4)** — `DEFAULT_MUTATE_TIMEOUT = 900` (up from 600), `MAX_MUTATE_TIMEOUT = 3600`, `_clamp_timeout`. `delegate_mutation` on `TimeoutExpired` returns `partial: True` + partial usage parsed from `e.stdout`. `mutate()` gains `timeout=`; keeps the worktree when there is a diff even on a partial; a partial never clears the gate (incomplete work isn't green regardless of tests).
4. **`--gc` (N3)** — `gc_worktrees()`: `git worktree prune`, then for each `codex/` worktree remove it only if `git status --porcelain` is empty; keep-and-report ones holding work (the N2 salvage lesson); never touch a non-codex worktree. No auto-nuke atexit — that would destroy the exact partial work N2 preserves.
5. **CLI** — `--timeout`, `--gc`, `--dry-run`.

## Files Expected To Change

- `scripts/conductor/mutate.py`
- NEW `tests/test_mutate_ergonomics.py`; `tests/test_mutate_scope.py` (renamed cost fields, cap-aware budget test)
- NEW delta `sdd-plus/changes/mutate-ergonomics/specs/codex-enforcement-bridge.md`
- `docs/AI_OPERATOR_GUIDE.md`

## Risks

- **Renamed cost fields are a contract change.** Mitigated: tests updated, and the release note calls it out; no external consumer beyond the operator reads them.
- **A wrong timeout could hang the operator.** Clamped to [60, 3600]; the default is bounded and a partial is always salvageable.
- **`--gc` deletes worktrees.** Blast-radius-bounded to `codex/` (inherited from `cleanup_worktree`), skips anything holding work, and `--dry-run` previews. A non-codex worktree is provably untouched (test).
- **Timeout doesn't auto-scale** (no fixed payload). Accepted: raised default + operator lever, stated in the brief.

## Rollback

Additive except the two renamed cost fields. `git revert` clean; `--files`/`mutate()` callers unaffected (new params default). Reverting restores the 64KB cap and 600s timeout.
