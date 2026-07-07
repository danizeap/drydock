# Verification

## Change

completion-integrity

## Automated Checks

- [x] `python -m pytest tests/ -q` → **165 passed** (147 prior + 18 new in test_completion_gate.py). New tests cover: nudge-once-then-silent, pure-conversation silence, work-in-progress budget preservation, verification-filled silence, verification-only-task counts as done, deleting-verification does not evade, self-heal on missing state, session cap, merge-preserves-ledger-on-compact, startup-resets, untrusted session id, stop_hook_active short-circuit, non-Drydock silence, main-exit-0-on-bad-stdin, oversized/corrupt/foreign/hashed-filename state-file safety.
- [x] `python scripts/check_sync.py` → **OK, 10 pairs identical** (hooks are plugin-level, not scaffolded; the sdd.py pair is untouched this change).
- [x] `python scripts/release.py --check` → **OK at 0.2.0** (version lockstep unaffected; 0.2.1 CHANGELOG entry drafted).
- [x] Refactor safety: all 18 pre-existing `test_session_orient.py` tests still pass — the discovery extraction into `_drydock_common` is behavior-preserving.
- [x] CI completion_gate smoke (run locally): malformed/empty/missing-cwd/root-cwd payloads all exit 0.
- [x] `ast.parse` on `_drydock_common.py`, `session_orient.py`, `completion_gate.py` → OK. hooks.json valid with all 3 events (SessionStart, Stop, PreToolUse).

## Manual Checks

- [x] Ran a 3-adversary red-team of the design BEFORE implementation; every high/medium finding is defended in code and pinned by a test (shared module vs drift, content-hash vs mtime false-nudge, completion-shaped precondition vs budget-burn, persist-before-speak vs loop, merge vs compact re-arm, per-user hashed state file vs traversal/symlink/collision).
- [x] Confirmed the loop-killer: `completion_gate.run` returns the nudge name only if `write_state` succeeded; a persistence failure yields silence, never a re-fire.
- [x] Confirmed fail-polarity is silent-allow throughout (opposite the git/secrets guards) — deliberate, per decision-log, because a false block is catastrophic and a missed nudge is caught at archive.
- [x] Confirmed the nudge reason offers the deferral path and is provenance-neutral (never demands verification the Owner declined; never "fixes" files it may not have authored).

## Documentation Updates

- [x] Operator guide updated (4-hook inventory incl. completion_gate + the stamp on session_orient).
- [x] CHANGELOG `## 0.2.1 — completion integrity` drafted.
- [x] Specs updated: delta specs completion-gate.md (new) + session-orientation.md (ADDED requirement) — to be synced at archive; the session-orientation add is the repo's first ADD-to-an-existing-capability sync.
- [x] No README change needed. Reason: agent-side behavior; operator guide + CHANGELOG cover it.

## Independent Verification

- [x] `drydock:verifier` subagent review (FULL-mode gate) → **VERIFIED WITH NOTES** (2026-07-07). Independently re-ran pytest (165, incl. the 18 pre-existing session_orient tests still green), check_sync (10/10), release --check; mapped all 5 delta requirements to code + tests. **Adversarial mandate held on every axis:** drove the nudge-once-then-silent flow and the write-failure/compact/resume paths (no loop; ledger preserved across compact); confirmed silence on pure conversation, fresh 5-task scaffold, and filled verification (no false nudge); 9 malformed Stop payloads all exit 0; `session_id="../.."` → hashed filename, oversized/corrupt/foreign/bad-schema state all read as missing; both hooks confirmed to share `_drydock_common` discovery + fingerprint (no drift). Two non-blocking notes resolved: dead `_MAX_WALK` constant removed from session_orient.py; the version staying 0.2.0 is the intended pre-release state.

## Result

**PASS.** Implementation complete and independently verified: 165 tests green, check_sync green, version lockstep intact; the Stop gate is proven loop-safe (persist-before-speak), false-nudge-free (three ANDed conditions + completion-shaped precondition), never-break (all-exit-0), self-healing, and state-safe — built against a pre-implementation red-team and confirmed by an adversarial verifier. Remaining (Owner-gated): the v0.2.1 cut via `release.py 0.2.1` and publish.
