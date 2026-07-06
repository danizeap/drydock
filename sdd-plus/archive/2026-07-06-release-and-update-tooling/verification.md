# Verification

## Change

release-and-update-tooling

## Automated Checks

- [x] `python -m pytest tests/ -q` -> **126 passed** (117 prior + 9 new in test_release.py). New tests cover: numeric (not lexical) version ordering, `--check` pass/drift, non-increasing-version rejection, missing-changelog rejection, dry-run writes nothing, and the full bump rewriting all locations while proving `git` is never executed (subprocess recorder asserts only pytest+check_sync ran).
- [x] `python scripts/check_sync.py` -> **OK: all 10 root/scaffold pairs identical** (no dual-copied file was touched; release.py/tests/CI/DEVELOPING.md are dev-only, not scaffolded).
- [x] `python scripts/release.py --check` -> **OK** after the operator-guide fix; before the fix it correctly reported `DRIFT: ['0.1.3', '0.1.5']` naming plugin.json/marketplace.json (0.1.5) vs operator-guide (0.1.3) — the live proof.
- [x] `python scripts/release.py 0.1.6 --dry-run` -> correctly **refuses** ("add a `## 0.1.6` section ... first") because no CHANGELOG entry exists yet.
- [x] `python -c "import ast; ast.parse(...)"` on scripts/release.py -> parses OK.

## Manual Checks

- [x] Confirmed the four version locations are exactly plugin.json, marketplace.json, the operator-guide VERSION line, and the CHANGELOG heading — historical mentions (archived packets, `schema_version: 0.1.0`, cache-path strings in settings) are intentionally excluded and untouched.
- [x] Read release.py end-to-end: it invokes `subprocess.run` only for pytest and check_sync; the git commit/tag/push commands are `print`-ed, never executed (also asserted by test).
- [x] DEVELOPING.md marks the exact `/plugin` local-install syntax as "confirm in your terminal" and gives the verified `git -C ...pull` fallback, rather than over-asserting commands I could not run from here.

## Documentation Updates

- [x] README updated (Updating note + link to DEVELOPING.md).
- [x] docs/AI_OPERATOR_GUIDE.md updated (VERSION line fixed; troubleshooting row for stale marketplace clone).
- [x] docs/DEVELOPING.md added (update flow, local dev-install, release process, version-location table).
- [x] Specs updated: delta spec specs/release-tooling.md (to be synced into a living capability spec at archive).
- [ ] No documentation update needed. Reason: n/a (docs were the point).

## Independent Verification

- [x] `drydock:verifier` subagent review (STANDARD-mode gate) → **VERIFIED** (2026-07-06). Independently re-ran pytest (126 passed), check_sync (exit 0), release.py --check (exit 0); confirmed by code inspection + negative test that release.py never spawns git (single subprocess.run, argv only pytest/check_sync; git commands are printed strings); exercised the drift detector in a temp copy (rc=1 naming both values on 0.1.3-vs-0.1.5 drift, rc=0 aligned); confirmed dry-run writes nothing, all 4 delta requirements IMPLEMENTED with file:line + real tests, no scope creep, no secrets, no scaffold drift.

## Result

**PASS.** Implementation complete and independently verified: 126 tests green, check_sync green, version lockstep enforced and CI-wired, release.py proven to never execute git. The stale operator-guide version (drifted through four releases) is fixed and now guarded. Remaining (Owner-gated): write real `## 0.1.6` CHANGELOG notes, run `python scripts/release.py 0.1.6`, and publish with the printed git commands.
