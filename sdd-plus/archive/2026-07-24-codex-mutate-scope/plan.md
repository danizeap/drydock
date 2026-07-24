# Plan

## Change

codex-mutate-scope

## Approach

1. **Metering (`summarize_cost`)** — `delegate_mutation` already parses `usage` off Codex's `turn.completed` event and discards it. `mutate()` now reads the fuel gauge **before and after** the delegation and reports:
   - normalized token counts (both `input_tokens`/`prompt_tokens` spellings; cached-input carried separately),
   - `fuel_used_percent` as the **authoritative** cost — it is what the account was charged,
   - `elapsed_s`.
   Every field is `None` when unmeasurable. A mid-run window reset makes `after < before`, so a negative delta is reported as unmeasured rather than as a number.
2. **Soft scoping (`--files`, `build_scoped_task`)** — named targets are read from the **worktree** and inlined behind the same escalating boundary marker `review.py` uses, with a preamble telling Codex to start there, that it may still edit coupled files, and that anything outside is reported rather than blocked. Guarded exactly like an explicitly named review path: refuse on secret-by-name, refuse on secret-by-content, cap the inline budget. A named file that does not exist yet is legal (it may be the file to create).
3. **Disclosure (`assess_scope`)** — after the diff is extracted, compare declared vs touched: `out_of_scope`, `declared_untouched`, `honored`. Feeds a non-gating advisory.
4. **Diff shape (`describe_diff_shape`)** — parse added lines per file, reduce each to a **structural signature** (identifiers → `#`, numbers → `0`, punctuation kept), then take the mean best-pair Jaccard across files. Wide + low repetition → `wide-divergent`, which raises an advisory saying the test gate is weak evidence here. Wide + high repetition is a mechanical sweep and says nothing.
5. **CLI** — `--files PATH [PATH ...]`, documented as opt-in and best for a small coupled change.

## Files Expected To Change

- `scripts/conductor/mutate.py`
- `scripts/conductor/review.py` (expose `content_has_secret` as a public name for reuse)
- NEW `tests/test_mutate_scope.py`
- NEW delta `sdd-plus/changes/codex-mutate-scope/specs/codex-enforcement-bridge.md`
- `docs/AI_OPERATOR_GUIDE.md`

## Risks

- **Structural signatures are a heuristic.** Erasing identifiers can make genuinely different work look similar (two unrelated one-line guard clauses share a shape). The consequence is a **missed advisory, never a false gate** — the failure direction is chosen deliberately and stated rather than hidden.
- **Thresholds are provisional.** `WIDE_DIFF_FILES=8` / `LOW_REPETITION=0.45` come from reasoning, not data. They stay advisory-only until calibrated against real diffs; the emitted `diff_shape` carries its own thresholds so any judgment can be re-derived later.
- **The after-gauge read adds a second app-server call** per mutation (no tokens, a few seconds). Acceptable for an operation already measured in minutes.
- **Codex's rate-limit reporting may lag the turn.** If it does, `fuel_used_percent` under-reports. Token counts are the cross-check; this is a stated limit, not a claim of exactness.
- **Under-scoping is expected.** Naming too few files is the normal failure — which is exactly why the scope is soft and out-of-scope edits are disclosed rather than blocked.

## Rollback

Additive. Omitting `--files` reproduces prior behavior (regression-tested); `cost`, `scope` and `diff_shape` are additional result keys; `assess_gate`'s new parameters default to `None`. `git revert` clean.
