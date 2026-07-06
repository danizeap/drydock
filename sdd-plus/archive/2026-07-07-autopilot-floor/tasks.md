# Tasks

## Change

autopilot-floor

## Implementation

- [x] Write delta specs (session-orientation new capability; change-packet-gates governed-override ADDED requirement).
- [x] Red-team the session_orient design (4 adversaries; folded every high/medium finding into the implementation and delta-spec scenarios).
- [x] Governed --force in sdd.py (--reason required; override record appended to decision-log) + sync scaffold copy.
- [x] Build hooks/session_orient.py (read-only scan; no-op outside Drydock; always exit 0; bounded discovery; untrusted-cwd handling).
- [x] Add guardrail liveness self-test (live only if exit==2 + expected message + benign control==0; else degraded; + static hooks.json wiring check).
- [x] Wire hooks.json SessionStart entry (python3||python, startup|resume|clear|compact).
- [x] Tests: test_session_orient.py (18 tests) + governed-force tests in test_sdd_gates.py (3).
- [x] CI smoke test (orient always exits 0) + docs (operator guide, CHANGELOG 0.2.0).
- [x] Run suite + check_sync green (147 tests; 10 pairs identical).
- [x] Independent verifier subagent review → VERIFIED; adversarial mandate held (no false "live", no session block, no foreign orientation, no leak).
