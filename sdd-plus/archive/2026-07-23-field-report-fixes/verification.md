# Verification

## Change

field-report-fixes

## Automated Checks

- [x] `python -m pytest tests/test_mutate.py -q` → 27 passed. Covers: masking forms untrusted (`|`, `;`, `&`, `||`, newline, backtick, `$( )`); safe forms trusted (`&&` chain, `2>&1`, quoted `-k "a and b"`); platform-aware quoting (`'a|b'` is a real pipeline on cmd.exe); fail-closed default when the trust key is absent; broken-env never green; coverage-gap advisory on/off; runner-delegation disclosed but non-gating; the `unverifiable` reason names its actual cause; `_looks_like_test` precise.
- [x] `python -m pytest -q` (full suite) → 361 passed, 3 skipped — no regressions.
- [x] `python scripts/check_sync.py` → 11 pairs identical.
- [x] Reproduce-before-fix: committed `HEAD` gave `run_tests("exit 1 | cat") -> pass:True` and `assess_gate -> green, clears:True`. Confirmed the reported 0.8.0 defect was real.
- [x] Ground-truthed end-to-end on the real shell: `… & echo hi`, `… 'x|echo hi'`, `… | more`, `… || echo hi` all report shell exit 0 on a FAILING command yet now yield `unverifiable / clears:false`; controls hold (honest pass → green, honest fail → red, `&&` chain → green).

## Manual Checks

- [x] Independent `verifier` subagent, **two rounds**.
  - **Round 1: NOT VERIFIED.** The first fix was a blacklist detecting only `|`. The verifier falsified it with working counterexamples on both shells — including on the Owner's own platform: `test & echo hi` (cmd.exe sequencing) and `'x|echo hi'` (cmd.exe does not quote with `'`, so a POSIX-style scanner walks past a real pipeline) both still produced `green` on a failing test; plus `;`, `&`, newline and an escaped-quote form on POSIX. It also flagged `exit_code_trusted` defaulting to **True** (a safety gate assuming trust) with a test enshrining it, and that verification had been marked done against an untouched template.
  - **Round 2: VERIFIED WITH NOTES.** Re-attacked with the same method (real-shell ground truth, both quoting models, end-to-end through `run_tests` + `assess_gate`): *"All eight of my working counterexamples now return `unverifiable, clears: false` … none of the 23 realistic honest commands are over-blocked."* Fail-closed default confirmed; advisories proven non-gating (0/18 mismatches); `_looks_like_test` confirmed precise.
- [x] Round-2 notes resolved: the `unverifiable` reason now names its actual trigger (was hard-coded to "pipe/or-list"); the delta spec R10, brief scope/stop-condition, and plan risks were rewritten to describe the allow-list rather than the rejected blacklist (critical — `/drydock:sync` would otherwise have merged the *rejected* design into the living capability spec).
- [x] **Declared limit, disclosed rather than hidden:** the gate judges the top-level command's SHAPE only. Masking *inside* a delegated script (`npm run ci` whose package.json script pipes; `bash -c "false; true"`) is invisible to any top-level scan — `bash -c "…"` genuinely is a simple command. This is now (a) stated in R10, the brief and the plan, and (b) surfaced at point of use as an advisory naming the runner. Not detectable, therefore not claimed as covered.

## Documentation Updates

- [x] Specs: delta `specs/codex-conductor.md` — R10 rewritten (allow-list + fail-closed + limit), R23–R25 added.
- [ ] Operator guide: the gate section still predates the `unverifiable` verdict; folded into the next docs pass with the field report's triangulation story.
- [ ] No documentation update needed. Reason:

## Result

VERIFIED. The field report's HIGH finding is closed at the class level, not the instance level: trust is now an allow-list where unrecognised constructs and an absent trust signal both default to untrusted, and the verifier could not falsify it on either shell. 6.2, 6.4, 6.5, 6.6, 6.7 are implemented and covered. One limit (masking inside a delegated script) is honestly disclosed in the spec and at runtime rather than papered over. Ready for `/drydock:sync` then archive.
