# Verification

## Change

codex-review-command

## Automated Checks

- [x] `python -m pytest tests/test_codex_review.py -q` → 7 passed (fake Codex, zero account quota): happy path, light→workhorse routing, secret refusal, no-core, missing file, oversized-file rejection, untrusted-data framing.
- [x] `python -m pytest -q` (full suite) → 310 passed, 3 skipped — no regressions.
- [x] `python scripts/check_sync.py` → 11 pairs identical (new files are plugin-level, no scaffold twin).

## Manual Checks

- [x] Live round-trip exercised: `python scripts/conductor/review.py scripts/conductor/review.py` returned a real flagship review (exit 0, ~17K input tokens, 95% fuel). Codex flagged 4 issues in the CLI itself; each was audited (not rubber-stamped) — 3 CONFIRMED (prompt-injection framing, unbounded reads, uncaught read errors) and fixed; 1 REFINED (TOCTOU severity overstated — guard is name-based, no double read — but the cheap realpath/symlink mitigation was taken). This is the mutual-audit loop working on the command's own code.

## Documentation Updates

- [x] README/operator-guide: `docs/AI_OPERATOR_GUIDE.md` command count 10 → 11 (adds `/drydock:codex-review`).
- [x] Specs: delta `specs/codex-conductor.md` (ADDED review-command requirement), to be synced into the living `codex-conductor` capability.
- [ ] No documentation update needed. Reason:

## Result

VERIFIED. The read-only conductor is now usable in-session via `/drydock:codex-review`: Codex reviews, Claude audits. Structured for every outcome, secret-guarded (paths + realpaths), size-capped, injection-framed, zero quota in CI. Ready for `/drydock:sync` then archive.
