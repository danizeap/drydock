# Tasks

## Change

executor-fleet

## Implementation

- [x] `scripts/conductor/executors.py` — `Executor` interface, `CodexExecutor` (proven, wraps `codex_bridge`), `KimiExecutor` (staged/unverified), registry + `DRYDOCK_EXECUTORS` stack config, `fleet_status()`.
- [x] `tests/test_executors.py` — Codex fuel via fake; Kimi refuses + never usable even when present; fleet_status usable/staged; stack config pins the set (no quota).
- [x] Delta spec `specs/codex-conductor.md` (executor-fleet requirements).
- [x] Capture the product decision in `sdd-plus/specs/multi-agent-orchestration-vision.md`; Kimi-pending memory.
- [x] Run verification — executor tests 7 passed; full suite green; check_sync 11/11; live `fleet_status` shows Codex usable @95%, Kimi absent.
