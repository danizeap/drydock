# Verification

## Change

owner-brief

## Automated Checks

- [x] `python -m pytest tests/ -q` — **251 passed, 2 skipped** (197 base → +54 new; the 2 skips are symlink tests on Windows without privileges, by design). Run by the implementing session and independently by the verifier in both rounds.
- [x] `python scripts/check_sync.py` — OK 10/10; **no new pair** (brief.py is deliberately plugin-only).
- [x] `python scripts/release.py --check` — all locations agree (version bump is the release step, not this packet).
- [x] Live engine on this repo: `python scripts/brief.py` → valid FACTS block; owner-brief rendered at built-not-checked (the honest rung while this file was Pending); six archives done-documented; guardrail history bounded ("1 session since 2026-07-07", older-history flag set).
- [x] Live `--write-status --lang es` → deterministic Spanish OWNER_STATUS.md with visible staleness header, HEAD sha, fp+lang comment; no-change rerun → `written: false, unchanged`; language preserved without --lang.
- [x] Falsification of the verdict-delivery tests (anti-vacuity proof): an asymmetric sabotage (output on the ledger-refusal path only) makes all three subprocess tests FAIL; reverted; suite green. A prior symmetric sabotage correctly did NOT fail them (differential tests cannot see identical corruption in both arms — bounded by the healthy-arm content assertions). The verifier independently reproduced the falsification on scratch copies with the same outcome.

## Manual Checks

- [x] Verifier live-adversarial attempts, all held: forged headingless "PASS." → no ascent; "Passed all checks" → record-not-pass; Override archive → demoted; `--record-verify` on a gate-failing packet → `gate-failed`, ledger byte-identical; OWNER_STATUS.md Write/Bash-append denied WITH an active packet; `docs/OWNER_STATUS.md` (soft segment) → silent; probes with DRYDOCK_PROBE=1 → still exit 2, zero ledger lines; sentinel fires on the real stale file, only on startup/clear.
- [x] Import anchoring: decoy `_drydock_common.py` planted in cwd and project root is never executed (test + verifier check).
- [x] Session incident, disclosed and recovered: a `git restore hooks/_drydock_common.py` during the falsification round reverted that uncommitted file to the v0.2.3 base; both lost edits were re-applied from context; the verifier confirmed the recovered file **byte-identical to the version it reviewed pre-accident** (same diff stat, same content at same line numbers). Product note filed: git-safety deliberately allows single-file discards — the conservative choice that enabled this; candidate warn-tier consideration for a future packet.

## Documentation Updates

- [x] README or user-facing docs updated, if needed. (README "It reports to you — in your language" + commands row; operator guide: 10 commands, brief-engine row with authority order + state-dir diagnostic, updated hook row; CI brief-engine smoke; commands: brief.md new, verify/new/archive/status wired.)
- [x] Project context updated, if needed. (Not needed — no change to what the project is.)
- [x] Specs updated, if needed. (Three delta specs; synced at archive.)
- [ ] No documentation update needed. Reason: n/a — the Owner surface is documentation-facing by nature.

## Independent Review

`drydock:verifier`, adversarial mandate, two rounds:

1. **Round 1: NOT VERIFIED — on evidence, not behavior.** Every behavioral claim held under live attack, but the flagship verdict-delivery-independence test was proven **vacuous** twice over: its cwd carried no Drydock markers (append path never reached — both compared runs did zero ledger I/O) and its "broken" env wasn't broken (candidate-base fallback made appends succeed elsewhere). Acceptance criterion "test-pinned for all four writers" was checked but false. Four smaller notes: completion-gate append-timing spec overpromise; misnamed test with warn/status-file appends untested through main(); stale "being-built" live claim; docstring/spec-wording cosmetics.
2. **Fix round:** tests rebuilt structurally anti-vacuous (healthy arm must prove the append happened; broken arm is a directory at the journal's own path, immune to base fallback; per-writer coverage incl. a raising ledger against the completion gate); spec wording aligned to code; tests split and warn/status-file appends exercised through main(); docstring fixed.
3. **Round 2: VERIFIED WITH NOTES.** All five discrepancies confirmed fixed; detection power independently falsification-tested; recovery confirmed byte-identical; "I could not construct a way for these tests to pass with the invariant broken, short of a deliberate future redesign." Residual notes (non-blocking, recorded for future work): the broken arm pins the lstat-refusal branch specifically — if append ever gains write-side base fallback, re-examine; the completion-gate pin covers run() not main()'s formatting; a true hang remains physically untestable (bounded by no-fsync + append-after-delivery); this file's filling was the one open task.

## Result

PASS. Two-round adversarial verification: behavior confirmed under live attack in round 1, evidence quality repaired and re-confirmed in round 2 (VERIFIED WITH NOTES, notes residual not blocking). 251 tests, check_sync 10/10, falsification-proven regression net.
