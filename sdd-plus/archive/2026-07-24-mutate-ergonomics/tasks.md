# Tasks

## Change

mutate-ergonomics

## Implementation

- [x] `summarize_cost` — below-resolution/reset fuel → `null` + `fuel_resolution`; genuine no-op stays `0`; tokens made primary in the note; fields renamed to `fuel_used_before/after_percent`. `_num_or_none` still guards the boolean gauge.
- [x] `--files` caps imported from review (`MAX_FILE_BYTES`/`MAX_TOTAL_BYTES`) so a 90KB file is scopable and the two paths can't drift.
- [x] `delegate_mutation` returns `partial: True` + partial usage on timeout; `mutate()` keeps the worktree on a partial-with-changes, flags `partial`, and forces `clears_gate: False`; empty timeouts still cleaned up.
- [x] `--timeout` operator lever (`_clamp_timeout`, [60, 3600]); default raised 600 → 900.
- [x] `gc_worktrees()` + `--gc`/`--dry-run` — removes empty `codex/` orphans, keeps ones holding work, never touches a non-codex worktree.
- [x] `tests/test_mutate_ergonomics.py` (16 tests: fuel resolution incl. the reporter's exact run-D numbers, unified caps + 90KB scopable, timeout clamp/passthrough/partial-salvage/empty-cleanup/usage-capture, gc empty/uncommitted-work/committed-work/fail-safe/non-codex/dry-run); `tests/test_mutate_scope.py` updated for renamed fields and the larger budget.
- [x] Dogfooded `--gc --dry-run` on this repo (clean, no orphans) and re-ran the reporter's run-D numbers through the fixed cost fn (`0` → `null` + "below gauge resolution").
- [x] **Verifier Finding 1 fix**: `--gc` judged "has work" by `git status` (uncommitted only), so a codex worktree that COMMITTED its work read as empty and was force-deleted. Added `_worktree_has_work` — keeps a worktree with uncommitted changes OR commits unique to its codex branch (`git branch --contains`), fails safe (keep) on any probe error. R8 strengthened to match; the overclaiming "genuinely empty" comment corrected.
- [x] `docs/AI_OPERATOR_GUIDE.md` — mutating-delegation paragraph: cost reframe, `--timeout`, partial salvage, `--gc`.
- [x] Run verification — three mutate files 84 passed/1 skipped; full suite **458 passed, 6 skipped**; check_sync 11/11; `verifier` subagent (VERIFIED WITH NOTES, all findings addressed).
