# Tasks

## Change

codex-mutate-scope

## Implementation

- [x] `summarize_cost()` — normalized token counts (both usage spellings, cached-input separate), authoritative `fuel_used_percent` from a before/after gauge read, `elapsed_s`; `null` for anything unmeasurable, and `null` rather than a negative when the window resets mid-run.
- [x] `mutate()` reads the gauge after the delegation and reports `cost` + `gauge_after` alongside the existing `gauge`.
- [x] `build_scoped_task()` — opt-in `--files` inlines the named targets behind the escalating boundary marker, with a preamble that permits coupled edits and states they will be reported.
- [x] Secret guard on inlining: by-name and by-content refusal (`stage: scope_guard`) **before** Codex is spawned; inline budget capped; a not-yet-existing target stays legal.
- [x] `assess_scope()` — `declared` / `out_of_scope` / `declared_untouched` / `honored`, feeding a non-gating advisory.
- [x] `describe_diff_shape()` — structural signatures (identifiers → `#`, numbers → `0`), mean best-pair Jaccard across files, `narrow` / `wide-repetitive` / `wide-divergent`, thresholds emitted with the measurement.
- [x] `assess_gate()` takes `diff_shape` and `scope` and raises advisories only — verdict and `clears` untouched.
- [x] `review.content_has_secret` made public for reuse (the internal name kept as an alias).
- [x] `tests/test_mutate_scope.py` — **41 tests**: cost math and null-not-zero, the mid-run reset, garbage payloads; inlining, both secret refusals, fence escalation, budget caps, opt-in no-op; scope disclosure including the reporter's own 3-file shape; sweep-vs-divergent shape with the advisory proven non-gating; end-to-end cost+scope and a pre-spawn refusal.
- [x] Operator guide: mutating-delegation paragraph gains cost reporting, `--files`, and the diff-shape advisory.
- [x] **Verifier round-1 fixes** (VERIFIED WITH NOTES, 4 blockers + 8 notes): boolean gauge readings produced a fabricated delta and a literal `0` (`_num_or_none`); `total_tokens` folded an unmeasured component into zero; `--files` had no worktree containment, no `realpath` in the name guard, no per-file cap and an uncapped stat-then-read, and no cap on the *number* of names; `lstrip("./")` mangled every dotfile into a false out-of-scope advisory; the diff parser was hijackable by an added line reading `++ b/x.py`, letting the delegate suppress its own advisory; `wide-repetitive` was asserted from an absent measurement (now `unknown`); the quadratic comparison is bounded and discloses sampling.
- [x] **Spec corrected where it was loose**: R4 scenario 1 was satisfiable by a measure-nothing stub — it now requires a measured `repetition` and `compared_files >= 2`. R3 gained the alias, containment and cap scenarios, plus an honest **stated limit**: a hardlink defeats every path-resolution guard (`review.py` shares it), so it is disclosed rather than implied covered.
- [x] **Confirmation-pass fixes**: the parser-hijack regression test passed against the very parser it guards (poison line was at the end of the last file, so the broken parser had nothing left to steal) — moved mid-file and proven to fail against a reimplemented pre-fix parser; added the missing R3 scenario-6 test (hard-capped read when the size check is lied to); reworded R4's mechanism clause as an observable property.
- [x] Run verification — review suite **68 passed, 1 skipped**; full suite **442 passed, 6 skipped**; check_sync 11/11; two `verifier` passes against frozen trees, the second confirming the spec rewrite is a tightening rather than a retrofit.
