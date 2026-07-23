# Plan

## Change

field-report-fixes

## Approach

1. **`mutate.py` — trust, not just pass/fail.**
   - `_has_shell_masking(cmd)`: **allow-list** — trusted only if the command is a simple command optionally `&&`-chained. A pipe, `;`/`&` sequencing, `||`, newline, backtick or `$( )` makes the exit code untrustworthy; `2>&1` stays trusted (a redirect, not a separator). Quoting is platform-aware (cmd.exe does not quote with `'`; POSIX backslash escapes honoured). Unrecognised constructs default to UNTRUSTED.
   - `_looks_like_test(path)`: path-segment / filename-precise (must not count `latest.py`, `inspector.py`, `contest.ts`).
   - `run_tests()` now returns `exit_code_trusted` and `env_warning` (worktree has `package.json` but no `node_modules`) alongside `ran`/`pass`.
   - `assess_gate()` gains verdict **`unverifiable`** (`clears: false`) when the exit code is untrusted OR the env is broken — checked BEFORE the pass branch so an untrustworthy success can never reach `green`. Adds an `advisories` list carrying the coverage-gap note.
2. **`handoff.py`** — `_packets()` returns (all un-archived, in-flight); in-flight = unchecked `- [ ]` in tasks.md or a Pending/TBD verification. `gather_state` reports `packets` + `in_flight_packets`; the render shows in-flight with an un-archived count. `write` emits `path` (plus `wrote` for compat).
3. **`review.py` / `review_schema.json`** — each finding requires a `file`; the prompt instructs Codex to set it.
4. Regression tests for every item; reproduce-before-fix on 6.1.

## Files Expected To Change

- `scripts/conductor/mutate.py`, `scripts/conductor/handoff.py`, `scripts/conductor/review.py`, `scripts/conductor/review_schema.json`
- `tests/test_mutate.py`, `tests/test_handoff.py`
- NEW delta `sdd-plus/changes/field-report-fixes/specs/codex-conductor.md`

## Risks

- **Over-blocking** — refusing green too eagerly would make the gate annoying and invite bypass. Mitigated by carving out the safe forms (`&&` chains, `2>&1`) and verifying against a sweep of realistic commands (`pytest -q`, `npm test`, `npx vitest run`, `cargo test`, `go test ./...`, `make test`, `-k "not slow"`, …) — none flagged; honest pass→green and honest fail→red are covered by explicit control tests.
- **Declared limit — masking inside a delegated script.** The allow-list judges the top-level command's SHAPE only; `npm run ci` or `bash -c "false; true"` can mask internally where no string scan can see. Not detectable — so it is DISCLOSED as an advisory at point of use and stated in the spec, never silently trusted.
- **Quoting differs by shell** — `'` quotes on POSIX but not in cmd.exe (a naive POSIX scanner walks past a real `'a|b'` pipeline on Windows). Handled platform-aware, with POSIX backslash escapes consumed.
- **Key rename in handoff state** (`active_packets` → `packets`/`in_flight_packets`) — internal API, tests updated; the render is clearer as a result.

## Rollback

Additive, behaviour-narrowing edits (the gate becomes *more* conservative). `git revert` clean. No change to the read-only conductor, guards, worktree isolation, or the no-auto-merge property.
