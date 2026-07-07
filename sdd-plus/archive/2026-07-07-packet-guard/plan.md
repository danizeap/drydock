# Plan

## Change

packet-guard

## Approach

1. **Red-team first** (running): three adversaries on false positives, bypasses/blind spots, and integration/robustness. The deny and exempt lists are finalized FROM the findings, not before.
2. **Delta spec** for the new `packet-guard` capability; scenarios mirror the red-team defenses.
3. **`hooks/packet_guard.py`** — decision order, all inside the always-exit-0 harness:
   - Parse stdin; untrusted cwd/session rules as the other hooks; extract target path(s) — handle Write/Edit (`file_path`) and MultiEdit shapes.
   - Bounded Drydock discovery via `_drydock_common` (shared, no drift). Not a project → silent.
   - Normalize the target; outside the project root → silent. Exempt paths → silent.
   - Active packet under `sdd-plus/changes/` → silent.
   - High-risk match (narrow, red-team-approved list) → deny + fixed-template reason (recovery: `/drydock:new`).
   - Else → warn-once: allow + additionalContext; `warned` flag persisted to the v0.2.1 state file (atomic, best-effort; persistence failure → stay allow + skip the warn, mirroring persist-before-speak).
4. **Wire hooks.json** (third PreToolUse entry, python3||python). Tests: every red-team FP class, bypass acceptance tests, state-schema compat with completion_gate, MultiEdit shape, latency sanity. CI smoke. Docs.
5. Suite + check_sync; adversarial verifier (mandate: produce a wrongful deny — must fail); sync; archive.

## Files Expected To Change

- hooks/packet_guard.py (new), hooks/hooks.json, hooks/_drydock_common.py (only if a shared helper is genuinely needed)
- tests/test_packet_guard.py (new)
- .github/workflows/ci.yml, docs/AI_OPERATOR_GUIDE.md, CHANGELOG.md
- this packet + delta spec

## Risks

- **[HIGH] Wrongful deny** (the adoption killer). Defense: deny list narrow + exact-segment matched, finalized by red-team; deny requires BOTH no-packet AND high-risk; every FP scenario pinned by a test; adversarial verifier mandate targets exactly this.
- **[HIGH] Nag erosion.** Defense: warn once per session, session-global, persisted via the hardened state channel; warn text blesses LITE work explicitly.
- **[MEDIUM] Per-edit latency** (three PreToolUse hooks now). Defense: no subprocesses, bounded reads, single dir listing; budget asserted in tests.
- **[MEDIUM] State-file contention** with completion_gate (same JSON). Defense: read-modify-write via the same atomic helper; the two flags are independent keys; a lost warn-flag update degrades to one extra warn, never a loop or deny.
- **[LOW] "Decoy packet" bypass** (any-packet rule). Accepted and documented: a user gaming their own safety tool is out of threat model; the completion gate still polices the decoy.

## Rollback

Tracked text; `git revert`. The guard is disabled instantly by removing its hooks.json entry, with zero effect on the other hooks. No project-tree writes; state-file flag is optional and backward-compatible.
