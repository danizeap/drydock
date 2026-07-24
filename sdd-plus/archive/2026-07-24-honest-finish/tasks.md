# Tasks

## Change

honest-finish

## Implementation

- [x] `delta_heading_issues` — flags non-canonical level-3 requirement headings under `## ADDED Requirements`; ignores canonical `### Requirement:`, `#### Scenario:`, and out-of-section headings.
- [x] `packet_unfilled` — the file half of the unified done-predicate (placeholder residue / pending Result).
- [x] `archive_readiness(change_dir, caps_dir)` — the single read-only blocker list (unattributable / unsynced-capability / missing-requirement / incomplete); consumed by both verify's prompt and archive's gate.
- [x] `cmd_verify` — always lints grammar + warns; when green, prints exactly one ready line that FAILS TOWARD needs-sync (READY only on synced + canonical, never from an empty blocker list); `show_ready_prompt=False` for the archive path.
- [x] `cmd_archive` — refactored onto `archive_readiness` (behavior-preserving block/waive+record); no living-spec write.
- [x] `commands/verify.md` — the ready line and its fail-toward-sync guarantee.
- [x] Scaffold twin `assets/project-scaffold/scripts/sdd.py`; check_sync 11/11.
- [x] `tests/test_honest_finish.py` — grammar lint (flag/accept/out-of-section); readiness (clean/unsynced/incomplete); the ready prompt (READY / non-canonical-refuses / nearly-there / silent-when-pending); archive block-then-force-waive; the vacuous-pass hole closed as a named regression.
- [x] Dogfooded the prompt on a throwaway packet: non-canonical → warn + not-ready; canonical+synced → READY.
- [x] **Verifier Finding 1 fix**: corrected the "prompt and gate can never disagree" overclaim (they diverge on grammar — verify stricter, archive warned-but-permissive); pinned archive's warn-but-proceed behavior with a test; recorded the asymmetry as a deferred decision.
- [x] Run verification — honest-finish + gates 35 passed; full suite 471 passed / 6 skipped; check_sync 11/11; `verifier` subagent (VERIFIED WITH NOTES, Finding 1 addressed).
