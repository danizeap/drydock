# Verification

## Change

executor-fleet

## Automated Checks

- [x] `python -m pytest tests/test_executors.py -q` → 7 passed (fake Codex, zero quota): Codex available + real fuel read; Codex unavailable; Kimi unverified + refuses; a *present* Kimi is staged-only and never usable; fleet_status usable/staged split with Claude noted; `DRYDOCK_EXECUTORS` pins the set.
- [x] `python -m pytest -q` (full suite) → 331 passed, 3 skipped — no regressions.
- [x] `python scripts/check_sync.py` → 11 pairs identical (plugin-level module, no scaffold twin).
- [x] Live `python scripts/conductor/executors.py` → Codex usable @ 95% (resets ~127h), Kimi `available: false` (not installed), Claude noted as human-tracked, `usable: [codex]`, `staged: []`.

## Manual Checks

- [x] The honesty guarantee holds: the staged Kimi adapter cannot run and cannot be reported usable even when present (`test_kimi_present_is_staged_never_usable`, `test_fleet_status_kimi_present_is_staged_not_usable`). Presence (`available`) is code-separated from proven (`verified`), which is flipped only by an on-machine live-fire — the same discipline that caught the stale Codex binary.

## Documentation Updates

- [x] Project context: `sdd-plus/specs/multi-agent-orchestration-vision.md` — the product decision (hardcode Codex + Kimi, user-choosable stack, Kimi staged) captured.
- [x] Specs: delta `specs/codex-conductor.md` (R13–R16), to be synced into the living capability.
- [x] Memory: `codex-headless-integration` cross-links a Kimi-pending note (reality-check Kimi like Codex once installed).
- [ ] No documentation update needed. Reason:

## Result

VERIFIED. The conductor is now a fleet manager with a pluggable executor interface: Codex proven, Kimi staged (present-detection only, refuses to run, never usable until live-fire proven), a user-choosable stack, and an honest N-tank status that human-tracks Claude. Zero quota in CI. Ready for `/drydock:sync` then archive.
