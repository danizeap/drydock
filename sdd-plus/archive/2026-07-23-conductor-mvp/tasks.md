# Tasks

## Change

conductor-mvp

## Implementation

- [x] Delta spec `specs/codex-conductor.md` (read-only delegation + fuel gauge + safe-failure + secret-guard contract).
- [x] `scripts/conductor/__init__.py` + `scripts/conductor/codex_bridge.py` — `discover_core`, `read_rate_limits` (hardened), `delegate` (read-only, hardcoded safety flags + model-input validation + temp cleanup), `route`, `guard_outbound`.
- [x] `tests/fake_codex.py` — stand-in speaking the app-server handshake + emitting schema-conforming `exec` output (no quota).
- [x] `tests/test_codex_bridge.py` — discovery (newest / reject-sandbox / none), gauge (ok + spawn-error/early-exit/timeout/non-dict), delegate (result+usage parse, **argv asserts read-only, no `--dangerously*`/workspace-write**), model-injection refusal, secret refusal, route policy, opt-in live round-trip.
- [x] Docs — operator-guide "Codex as a read-only teammate" + vision §8 cross-link.
- [x] Run verification — `pytest` green (no quota spent), `check_sync` green, then the `verifier` subagent (VERIFIED WITH NOTES → all notes resolved).
