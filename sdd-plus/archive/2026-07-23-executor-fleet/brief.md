# Brief

## Change

executor-fleet — turn the conductor from "Claude + Codex" into a fleet manager with a pluggable executor interface, so the Owner can choose their stack (Claude alone / +Codex / +Kimi / all three). Codex ships as the proven adapter; Kimi ships STAGED — documented but unverified, refusing to run until reality-checked on install.

Intake: Mode STANDARD (a read-only interface + adapters wrapping already-verified code; no new mutating or security surface). Primary skill: `backend`; supporting: `mcp-ranger`. Approvals: Owner directed "hardcode Codex + Kimi, give the user the power to pick the stack; I'll install Kimi later and we reality-check it then." Stop conditions: any staged/unverified executor reported as usable or allowed to run; any executor claiming to work without an on-machine proof.

## What this means for your product

Drydock advertises a stack the Owner chooses: **Just Claude** (solo governed coding), **+Codex**, **+Kimi**, or **all three** (a fleet of frontier tanks with staggered refills + triangulated review). The conductor auto-detects what's installed and only uses what's been *proven* on the machine.

## User Need

Kimi K3 is frontier-tier at ~half the cost, but it isn't installed here yet. The Owner wants the architecture ready so Kimi (or any second executor) slots in as a small adapter later, without rework — and wants the honesty guarantee that nothing is treated as working until live-fire proven (the discipline that saved the Codex integration).

## Scope

In scope: `scripts/conductor/executors.py` — an `Executor` interface (`available`, `read_remaining`, `status`), a **CodexExecutor** (proven, wraps `codex_bridge`), a **KimiExecutor** (STAGED: present-detection only; `read_remaining` raises `ExecutorUnverified`; `verified=False`), a registry + `DRYDOCK_EXECUTORS` stack config (auto-detect by default), and `fleet_status()` (the N-tank picture; Claude noted as human-tracked). Tests (fake Codex, no quota). Delta spec + vision-note capture.

Out of scope: cross-executor routing + the fuel-aware endurance logic (next packet); the Kimi live-fire itself (needs Kimi installed); a `/drydock:fleet` command (fast-follow).

## Acceptance Criteria

- [ ] A staged/unverified executor (Kimi) is NEVER reported as `usable` and its `read_remaining`/run path REFUSES — even when present on the machine.
- [ ] `CodexExecutor` reads real fuel via the proven `codex_bridge`; `fleet_status()` shows usable vs staged and notes Claude as human-tracked.
- [ ] `DRYDOCK_EXECUTORS` pins the executor set; default auto-detects.
- [ ] Tests pass with zero Codex quota (fake); full suite green.

## Impact Areas

- Backend: new `executors.py` (interface + adapters + registry).
- API: the `Executor` contract + `fleet_status()`.
- AI/model behavior: the conductor becomes multi-executor aware (Codex live, Kimi staged).
- Documentation: vision-note capture of the product decision; Kimi-pending note.
- Operations/security: the honesty guarantee — unverified executors cannot run.

## Open Questions

- Stack selection UX at init (env var now; init-project prompt is a fast-follow).
