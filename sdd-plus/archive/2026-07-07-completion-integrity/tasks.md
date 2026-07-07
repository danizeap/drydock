# Tasks

## Change

completion-integrity

## Implementation

- [x] Red-team the Stop-hook design (3 adversaries: loop/nag, breakage/blind-spots, state-file surface); folded every high/medium finding into code + scenarios.
- [x] Write delta specs (completion-gate new; session-orientation ADDED requirement for the session-state stamp).
- [x] Extract shared hooks/_drydock_common.py (discovery + fingerprint + state I/O); refactor session_orient to import it + add the best-effort stamp (merge-not-overwrite on resume/compact).
- [x] Build hooks/completion_gate.py (claimed-done-but-Pending ∧ changed; per-packet nudge + session cap; persist-before-speak; self-heal; always exit 0).
- [x] Wire hooks.json Stop entry (python3||python).
- [x] Tests: test_completion_gate.py (18) covering nudge-once, loop-safety, false-nudge silence, self-heal, merge-on-compact, untrusted input, state-file attacks; session_orient tests still green after refactor.
- [x] CI smoke (completion_gate exits 0 on malformed inputs) + docs (operator guide 4-hook inventory, CHANGELOG 0.2.1).
- [x] Run suite + check_sync green (165 tests; 10 pairs identical).
- [x] Independent verifier subagent review → VERIFIED WITH NOTES; adversarial mandate held (no loop, no false nudge, no session break, state-safe). Notes resolved: dead _MAX_WALK constant removed; version-still-0.2.0 is the intended pre-release state.
