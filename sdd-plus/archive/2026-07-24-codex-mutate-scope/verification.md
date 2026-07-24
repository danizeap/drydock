# Verification

## Change

codex-mutate-scope

## Automated Checks

- [x] `pytest tests/test_mutate_scope.py tests/test_mutate.py -q` — **68 passed, 1 skipped** (the skip needs symlink-creation privilege).
- [x] `pytest` (full suite) — **442 passed, 6 skipped**.
- [x] `python scripts/check_sync.py` — OK, 11/11. **Null signal for this packet**: its pairs are root↔scaffold copies and cover none of `scripts/conductor/*`, `tests/*`, or `docs/AI_OPERATOR_GUIDE.md`. Recorded so the green is not mistaken for coverage.
- [x] Every requirement in the delta spec has a named regression test; the one scenario that cannot execute on this host is marked as such.

## Manual Checks

- [x] **The pre-existing suite was proven unchanged, not merely still-passing.** The verifier ran the unmodified `tests/test_mutate.py` against a shadow tree containing `git show HEAD:scripts/conductor/mutate.py` — 27 passed — and the same 27 against the new code. `assess_gate`'s two new parameters are keyword-defaulted and appended last; `mutate()`'s `files=` follows `keep=`; the `files`→`changed` rename is a local variable and the result dict still emits `"files"`, so the documented contract holds as a superset.
- [x] **The `review.py` rename is clean.** `rv._content_has_secret is rv.content_has_secret` → `True` (a binding, not a copy). Both names are exercised; breaking either fails 7–8 tests.
- [x] **The hardlink case was tested and found untestable-as-coverage**, so it is recorded as a limit instead of a guarantee. A hardlink has no target — both names are equal directory entries to one inode — so `realpath` returns the name it was given and no path-resolution guard can see through it. `test_hardlink_alias_is_a_STATED_limit_not_a_covered_case` asserts the current uncaught behavior and says why; if it ever starts failing, the guard got stronger and the limit can be retired.

## Requirement -> Test Mapping

| Requirement | Test |
| --- | --- |
| R1 cost reported: tokens + authoritative fuel delta | `test_cost_reports_tokens_and_authoritative_fuel_delta` |
| R1 alternate usage spelling | `test_cost_accepts_the_alternate_usage_spelling` |
| R1 **null, never zero** | `test_cost_is_null_not_zero_when_unmeasurable` |
| R1 **a boolean gauge cannot fabricate a number** | `test_cost_never_does_arithmetic_on_a_boolean_gauge` |
| R1 a partial token pair yields no total | `test_total_tokens_is_null_when_a_component_is_missing` |
| R1 mid-run window reset | `test_cost_delta_is_null_when_the_window_reset_mid_run` |
| R1 malformed usage payload | `test_cost_survives_a_garbage_usage_payload` |
| R2 opt-in no-op | `test_scoped_task_is_a_noop_without_files`, `test_mutate_without_files_is_unchanged` |
| R2 targets inlined | `test_scoped_task_inlines_named_targets` |
| R2 out-of-scope disclosed, not blocked | `test_scope_discloses_out_of_scope_edits_without_blocking`, `test_out_of_scope_edits_raise_an_advisory_but_never_gate` |
| R2 declared-but-untouched | `test_scope_reports_a_declared_file_codex_never_touched` |
| R2 nothing declared → `None` | `test_scope_is_absent_when_nothing_was_declared` |
| R2 **dotfiles not mangled** | `test_dotfile_targets_are_not_mangled_into_false_out_of_scope`, `test_leading_dot_slash_is_still_normalized` |
| R3 secret by name / by content | `test_scoped_task_refuses_a_secret_target_by_name`, `..._by_content` |
| R3 **symlink alias refused** | `test_scoped_task_guards_the_RESOLVED_path_not_just_the_name` — **SKIPPED on this host** (needs symlink privilege) |
| R3 **hardlink = stated limit** | `test_hardlink_alias_is_a_STATED_limit_not_a_covered_case` |
| R3 **worktree containment** | `test_scoped_task_refuses_a_path_outside_the_worktree` |
| R3 absolute path refused | `test_scoped_task_refuses_an_absolute_path` |
| R3 per-file cap / total budget / name count | `test_scoped_task_caps_each_file_not_just_the_total`, `test_scoped_task_budget_is_cumulative_across_many_small_files`, `test_scoped_task_caps_the_number_of_names` |
| R3 refusal before spawn | `test_mutate_refuses_before_spawning_when_a_target_is_secret` |
| R3 content cannot close its fence | `test_scoped_task_content_cannot_close_its_own_fence` |
| R4 sweep not flagged (measured) | `test_wide_mechanical_sweep_is_not_flagged` |
| R4 divergent flagged | `test_wide_divergent_diff_is_flagged_as_needing_a_real_read` |
| R4 **content cannot hijack the parser** | `test_added_content_cannot_hijack_the_diff_parser` |
| R4 **unmeasured ≠ reassuring** | `test_unmeasurable_repetition_is_unknown_not_reassuring`, `test_unmeasurable_narrow_diff_stays_narrow` |
| R4 basis ships with the verdict | `test_shape_reports_the_thresholds_and_what_it_compared` |
| R4 bounded comparison disclosed | `test_shape_comparison_is_bounded_and_says_so` |
| R4 advisory never gates | asserted inside both the divergent and unknown tests |
| R4 narrow / degenerate diffs | `test_narrow_diff_is_never_flagged_however_divergent`, `test_diff_shape_repetition_is_none_with_too_little_to_compare`, `test_diff_shape_survives_an_empty_or_malformed_diff` |
| shape normalization | `test_shape_erases_identifiers_but_keeps_structure` |

## Documentation Updates

- [x] `docs/AI_OPERATOR_GUIDE.md` — the mutating-delegation section now covers cost reporting, opt-in soft `--files`, and the diff-shape advisory.
- [x] Delta spec — R3 and R4 tightened to match what is actually enforced, with the hardlink limit stated rather than implied.
- [ ] Project context — no change needed; this extends an existing capability.

## Result

**Verified after one adversarial round.** The `verifier` returned **VERIFIED WITH NOTES** with four archive blockers and eight further findings. It confirmed every number claimed, proved the advisory-never-gates invariant by enumerating **1,260 combinations** of `(files × test_result × diff_shape × scope)` against the same calls without them — zero divergence — and mutation-tested the new suite: **21 of 25 injected defects caught**, with all tests failing against `HEAD`.

**The four blockers, all closed:**

1. **A boolean gauge reading fabricated the authoritative figure.** `isinstance(True, (int, float))` is `True`, and JSON `true` decodes to it, so `{"used_percent": True}` produced an arithmetic result — and `True`/`True` produced a literal `0`, the exact value R1 forbids and decision-log row 4 explicitly rejects. I had guarded the *token* path with `_int_or_none` and left the *gauge* path open. Now `_num_or_none`.
2. **R3 promised `review.py`'s treatment and delivered materially less** — no `realpath` in the name guard, no worktree containment (`--files ../../private.txt` read out-of-tree, confirmed present in the prompt), no per-file cap, and a stat-then-read that `review.py` had already been hardened against. All closed; the number of *names* is capped too, after 50,000 names built an 839 KB prompt in a change whose premise is a token blowout.
3. **The diff parser was hijackable by the party being reviewed.** An added source line reading `++ b/ghost.py` renders as `+++ b/ghost.py`; a prefix-matching parser read it as a file header, collapsed nine files into one phantom key, and the advisory vanished. Codex writes the diff, so this was self-suppression. The parser is now hunk-aware — `@@` line counts decide where a body ends, so content can never be mistaken for structure.
4. **`wide-repetitive` was asserted from an absent measurement.** A ten-file deletion sweep — entirely realistic — reported the reassuring case because `rep is None` fell through to the default. There is now an `unknown` kind with its own advisory, applying R1's own principle to R4.

**The loose requirement was real.** I asked the verifier to hunt for a requirement written loosely enough to be trivially satisfied, and R4 scenario 1 was exactly that: a measure-nothing stub satisfied **3 of R4's 4 normative clauses**. Rewritten to require a measured `repetition` and `compared_files >= 2`.

**Also fixed:** `total_tokens` folded a missing component into zero; `lstrip("./")` strips a character *set*, so every dotfile (`.github/…`) produced a false out-of-scope advisory; the two properties that were correct-but-untested (cumulative budget, thresholds emitted) now have tests; the quadratic comparison is bounded at 200 files and **discloses** sampling rather than truncating silently; `tasks.md` claimed 26 tests when there were 25 (now 41).

**Confirmation pass (frozen tree, md5s identical): VERIFIED WITH NOTES, nothing blocking.** All four blockers reproduced as closed — including the TOCTOU, where `os.fstat` was monkeypatched to under-report `st_size=10` on a genuinely 140KB file and the capped read still refused it. The symlink guard, unprovable on this host, was verified by intercepting resolution so an innocent name resolved to an in-tree `.env` (refused). The hardlink framing was checked for honesty and judged a limit pinned so it cannot silently rot, not a dressed-up hole.

**The spec rewrite was checked for retrofit and cleared.** Three stubs run against the new R4: *measure-nothing* → 5 failed; *constant-reassuring* (always `0.9`) → 7 failed. Scenarios 1 and 2 now pull in opposite directions, so no constant satisfies both, and scenario 3 forces `null`.

**One finding fixed after that pass, because it was the same species one level down.** `test_added_content_cannot_hijack_the_diff_parser` **passed against the vulnerable parser it exists to guard** — the poison line sat at the end of the last file, so the broken parser had nothing left to misattribute. A regression test that cannot detect its own regression is the F9 failure inside the test suite instead of the spec. The poison now sits mid-file with real content after it, and the test asserts every file keeps its own lines. Proven to discriminate: against a locally reimplemented pre-fix parser the assertions **fail** (10 keys, `ghost.py` present, `d7.py` robbed); against the shipped parser they pass (9 keys, intact). R3 scenario 6 (file grows during read) also gained the test it lacked — without it, dropping the `+1` from `fh.read(CAP + 1)` would have passed the entire suite while restoring the TOCTOU. R4's remaining mechanism-flavoured sentence ("derived from the diff's hunk structure") was rewritten as an observable property: no text a delegate can write may change which file the surrounding lines are attributed to.

**Known and accepted limits:** the thresholds (`8` files, `0.45` similarity) are reasoned, not measured — they stay advisory-only and ship inside the result so the judgment can be re-derived; a hardlink alias defeats path resolution and is stated, not covered; structural signatures can make genuinely different work look similar, which costs a missed advisory and never a false gate; Codex's rate-limit reporting may lag a turn, so `fuel_used_percent` can under-report and the token counts are the cross-check.
