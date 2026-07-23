# Tasks

## Change

field-report-fixes

## Implementation

- [x] Reproduce 6.1 before fixing (`exit 1 | cat` → gate reported `green, clears: true`).
- [x] `mutate.py` — `_has_shell_masking`/`_looks_like_test`; `run_tests` reports `exit_code_trusted` + `env_warning`; `assess_gate` gains the `unverifiable` verdict (checked before the pass branch) + an `advisories` list.
- [x] `handoff.py` — `_packets()` → (all, in-flight); `gather_state` reports `packets` + `in_flight_packets`; render shows in-flight + un-archived count; `write` emits `path` alongside `wrote`.
- [x] `review.py` + `review_schema.json` — required per-finding `file`; prompt instructs Codex to set it.
- [x] Regression tests: untrusted-exit-code never green; broken-env never green; piped-vs-plain trust detection; missing-node_modules detection; coverage-gap advisory on/off; finished packet not in-flight; in-flight packet surfaces.
- [x] **Round 1 verification returned NOT VERIFIED** — the verifier falsified the blacklist with working counterexamples on both shells (`&` sequencing and a cmd.exe `'a|b'` pipeline still greened a FAILING test), and flagged the fail-open `exit_code_trusted` default.
- [x] Hardening round: blacklist → **allow-list** (simple or `&&`-chained only; platform-aware quoting; unrecognised = untrusted), `exit_code_trusted` default inverted to **False**, `_looks_like_test` made precise, `_CODE_EXT` extended, reason string now names the actual cause, runner-delegation limit disclosed as an advisory.
- [x] Align artifacts with the final design (spec R10, brief scope + stop condition, plan risks) — the delta spec would otherwise sync the *rejected* design into the living capability.
- [x] Run verification — mutate suite 27 passed; full suite 361 passed; check_sync 11/11; `verifier` round 2 = **VERIFIED WITH NOTES** (could not falsify; all 8 counterexamples closed).
