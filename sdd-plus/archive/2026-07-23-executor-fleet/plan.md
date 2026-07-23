# Plan

## Change

executor-fleet

## Approach

`scripts/conductor/executors.py`:
1. `Executor` base — `available()`, `read_remaining()`, `status()`; class attrs `verified`, `subscription_window`. `status()` reports `available`/`verified` and only reads fuel when BOTH true; an available-but-unverified executor is marked `staged`, never usable.
2. `CodexExecutor(verified=True)` — `available()` = `codex_bridge.discover_core()` found; `read_remaining()` = `summarize_gauge(read_rate_limits(core))`. Wraps the proven bridge; no new logic.
3. `KimiExecutor(verified=False)` — `available()` = presence probe (`which(kimi…)` / `~/.kimi`|`~/.moonshot`); `read_remaining()` raises `ExecutorUnverified`. Carries the documented (unverified) invocation shape in the docstring for the future live-fire.
4. Registry + `DRYDOCK_EXECUTORS` stack config (default = all known); `executors()`, `fleet_status()`.
5. Tests: Codex fuel via fake; Kimi refuses + is never usable even when present; fleet_status usable/staged; stack config pins the set. Vision-note capture + Kimi-pending memory.

## Files Expected To Change

- NEW `scripts/conductor/executors.py`, `tests/test_executors.py`
- NEW delta `sdd-plus/changes/executor-fleet/specs/codex-conductor.md`
- `sdd-plus/specs/multi-agent-orchestration-vision.md` (product-decision capture)

## Risks

- **A staged executor treated as real** — the core risk. Mitigated: `verified` gates both `usable` membership and fuel-reads; `read_remaining` raises; a test proves a *present* Kimi is still staged-only.
- **Presence mistaken for readiness** — `available()` is presence only; `verified` is a separate, code-set flag flipped only after a live-fire proof.

## Rollback

All new files + one additive vision-note section. `git revert` clean; inert unless invoked. No change to `codex_bridge`, `mutate`, `review`, or the guards.
