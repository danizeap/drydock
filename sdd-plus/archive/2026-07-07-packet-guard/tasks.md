# Tasks

## Change

packet-guard

## Implementation

- [x] Red-team the PreToolUse design (3 adversaries: false positives, bypasses, integration); deny/exempt lists finalized from findings — `auth` demoted to warn, workflows deny only on creation, test/fixture segments suppress, Bash covered for the deny tier only.
- [x] Write the packet-guard delta spec + a completion-gate delta (shared-state writer contract, from the red-team's cross-hook finding).
- [x] Build hooks/packet_guard.py (silent/warn-once/deny; persist-before-warn; target-anchored discovery fallback; path-aware containment; always exit 0; never emits updatedInput).
- [x] Fix the v0.2.1 cross-hook bug: completion_gate now copy-and-updates shared state (foreign keys preserved); bash_write_targets moved to _drydock_common (secrets guard imports it — no drift).
- [x] Wire hooks.json third PreToolUse entry (Write|Edit|MultiEdit|Bash, python3||python).
- [x] Tests: test_packet_guard.py (28 after the fix round) — every red-team FP class, deny/suppression matrix, Bash deny, warn-once, persist-failure silence, cross-hook warned-preservation, garbage-stdin, one regression per verifier-found wrongful-deny class, MultiEdit + latency; full suite 193 green (protect_secrets refactor + completion_gate fix regression-checked).
- [x] CI smoke (packet_guard exits 0 on malformed inputs) + docs (operator guide 5-hook inventory, CHANGELOG 0.2.2).
- [x] Run suite + check_sync green.
- [x] Independent verifier subagent review → first pass NOT VERIFIED (3 wrongful-deny classes found — the mandate working); fix round; re-verification → VERIFIED WITH NOTES (classes dead, no new regressions); all notes resolved (spec clause narrowed, counts fixed, decision-log row amended, Dockerfile prefix tightened).
