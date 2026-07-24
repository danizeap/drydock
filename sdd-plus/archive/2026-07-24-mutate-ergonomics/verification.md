# Verification

## Change

mutate-ergonomics

## Automated Checks

- [x] `pytest tests/test_mutate_ergonomics.py tests/test_mutate_scope.py tests/test_mutate.py -q` — **84 passed, 1 skipped** (skip needs symlink privilege).
- [x] `pytest` (full suite) — **458 passed, 6 skipped**.
- [x] `python scripts/check_sync.py` — OK, 11/11. **Null signal for this packet**: its pairs are root↔scaffold copies covering none of `scripts/conductor/*`, `tests/*`, or `docs/AI_OPERATOR_GUIDE.md`.
- [x] Every R5–R8 scenario has a named regression test; the two new gc scenarios (committed work, fail-safe) were added after the verifier's Finding 1.

## Manual Checks

- [x] **Dogfooded** `mutate.py --gc --dry-run` on this repo (clean — no orphans) and the reporter's exact run-D numbers through the fixed cost fn: `input 181,184 / output 963` at gauge `10→10` now returns `fuel_used_percent: null`, `fuel_resolution: "below gauge resolution (<1% of the weekly window)"`, `total_tokens: 182147` — the value that read `0` is gone.
- [x] **Finding 1 reproduced then fixed.** The verifier's exact repro — a codex worktree that commits its work — read as empty under the old `git status` check and was force-deleted. Now `git branch --contains HEAD` keeps it; proven by `test_gc_keeps_a_codex_worktree_holding_COMMITTED_work`.
- [x] Pre-existing `tests/test_mutate.py` byte-unchanged and passing; the verifier confirmed the new tests fail against pre-change code (real invariants).

## Requirement -> Test Mapping

| Requirement | Test |
| --- | --- |
| R5 tokens + real fuel delta | `test_cost_reports_tokens_and_a_real_fuel_delta` |
| R5 below-resolution → null (reporter's run D) | `test_below_resolution_fuel_is_null_not_zero` |
| R5 no-op stays 0; reset vs resolution distinguished | `test_zero_delta_with_no_tokens_is_not_flagged_as_below_resolution`, `test_reset_and_below_resolution_are_distinguished` |
| R5 tokens primary in the note; renamed fields | `test_tokens_are_the_primary_signal_in_the_note`, `test_cost_is_null_not_zero_when_unmeasurable` |
| R5 boolean/garbage gauge guarded | `test_cost_never_does_arithmetic_on_a_boolean_gauge`, `test_cost_survives_a_garbage_usage_payload` |
| R6 caps == review, no drift | `test_files_caps_match_the_diff_caps` |
| R6 90KB file scopable | `test_a_ninety_kb_file_is_now_scopable` |
| R7 timeout keeps work, never clears | `test_timeout_keeps_the_partial_work_and_never_clears` |
| R7 empty timeout cleaned up | `test_timeout_that_wrote_nothing_is_cleaned_up` |
| R7 partial usage captured | `test_delegate_timeout_captures_partial_usage` |
| R7 timeout clamp + operator lever | `test_timeout_is_clamped_to_a_sane_range`, `test_operator_timeout_is_passed_through` |
| R8 empty orphan removed | `test_gc_removes_empty_orphans_but_keeps_work` |
| R8 **committed work kept** | `test_gc_keeps_a_codex_worktree_holding_COMMITTED_work` |
| R8 **fail-safe on probe error** | `test_gc_fails_safe_and_keeps_when_the_work_check_errors` |
| R8 non-codex untouched; dry-run | `test_gc_never_touches_a_non_codex_worktree`, `test_gc_dry_run_removes_nothing` |

## Documentation Updates

- [x] `docs/AI_OPERATOR_GUIDE.md` — cost reframe (tokens primary, below-resolution null), `--timeout`, partial salvage, `--gc`, shared caps.
- [x] Delta spec R5–R8; R8 strengthened for committed-work + fail-safe after Finding 1.
- [ ] Project context — no change; extends an existing capability.

## Result

**Verified after one adversarial round + a self-driven fix.** The `verifier` returned **VERIFIED WITH NOTES**: md5s identical start-to-end, every claimed number reproduced exactly, all five fixes match R5–R8, and every new test proven to fail against pre-change code (real invariants, none stub-satisfiable — it specifically checked, given the last two packets each hid one).

**Finding 1 (low, non-blocking) fixed anyway.** `--gc` judged work by `git status --porcelain`, which sees only *uncommitted* changes — so a codex worktree that committed its work read as empty and was force-deleted, commits dangling. Not a spec violation (R8 said "uncommitted") and not reachable by drydock's own flow (it never commits inside a worktree), but the code comment claimed "genuinely empty" while `has_work` only meant "no uncommitted changes" — the **third** overclaiming-comment of this session. Fixed by strengthening the guarantee rather than lowering the words: `_worktree_has_work` now also keeps a worktree whose tip is unique to its codex branch (`git branch --contains`), and fails safe (keep) on any probe error. R8 gained both scenarios; both have tests.

**Finding 2 (info) accepted:** a codex worktree whose directory was externally deleted has its admin entry pruned before gc reads the list, so its branch persists rather than being cleaned — errs toward keeping, no deletion risk. Left as-is.

**Known limits:** the mutate timeout can't auto-scale (no fixed payload — Codex reads the whole tree), so this ships a raised default + operator lever, stated. `--gc`'s committed-work check treats a tip already on a mainline branch as "no unique work"; a codex branch deliberately based on another codex branch is kept (fails safe).
