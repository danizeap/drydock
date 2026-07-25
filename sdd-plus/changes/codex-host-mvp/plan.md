# Plan

## Change

codex-host-mvp

## Approach

Use an additive adapter strategy. Preserve the existing Claude plugin and
shared lifecycle, then add Codex-specific packaging and integration around
them. The authenticated Claude CLI round trip and no-blocker cross-model
re-review are now proven. Do not begin implementation until the Owner approves
`docs/CODEX_HOST_BUILD_BLUEPRINT.md`.

1. Close the cross-model architecture review: prove authenticated Claude,
   reconcile all blocking concerns, and freeze threat, pace, adapter,
   negotiation, and worktree contracts.
2. Correct the enforcement and host-boundary documentation.
3. Add the Codex plugin manifest, thin lifecycle skills, and readiness
   reporting.
4. Add Codex-native hooks that reuse only independently tested pure policy
   primitives, use narrow matchers for supported side-effect contracts, deny a
   mismatch inside a matched hook, report unmatched tools as uncovered, and
   use `commandWindows`. Keep stateful lifecycle hooks host-native.
5. Build a deterministic plain UTF-8/LF single-file hook runtime bundle. A
   minimal program contained literally in the trusted hook command reads the
   runtime bytes once, validates the exact digest and manifest, starts the
   interpreter in isolated/no-site mode, pins imports to trusted
   standard-library roots, and executes those same bytes in memory. CI rebuilds
   and compares exact bytes beside `check_sync.py`; release repeats the check.
6. Add a separate-process mutation runner with fixed `workspace-write` and
   canonical worktree-root arguments, an atomic exclusive lease with bounded
   stale/dead-process reclamation, runner-owned Git metadata operations,
   Owner-state fingerprints, applicability-first tests,
   timeout/untrusted-never-green behavior, no auto-merge, and bounded cleanup
   including orphaned leases. Project-scoped nested agents remain advisory
   rather than a mutation boundary.
7. Add a separate-process read-only verifier with repository fingerprinting,
   while describing this as process/context/permission isolation rather than
   cross-model independence.
8. Extract a host-neutral orchestration controller and add a dedicated Claude
   peer adapter; keep the current Codex bridge as the Claude-host adapter.
   Preserve the bounded `negotiate.py` behavior and pace-first routing policy.
9. Dogfood the complete flow, cross-review it, run independent verification,
   and complete LaunchGuardian review.

## Files Expected To Change

- `adapters/codex/drydock/.codex-plugin/plugin.json`
- Plugin-root Codex skills, hooks, scripts, and assets under
  `adapters/codex/drydock/`.
- A deterministic packaged project-scaffold bundle and its rebuild checker,
  generated from the authoritative `assets/project-scaffold/` tree.
- New Codex-owned regression-test paths for the first slice.
- `assets/project-scaffold/.codex/` for project-scoped advisory agents and
  readiness state.
- `docs/AI_OPERATOR_GUIDE.md`, setup/README material, and relevant capability
  specs.
- LaunchGuardian records for the eventual release.

The first implementation slice SHALL NOT edit `scripts/sdd.py` or its scaffold
twin, `scripts/conductor/`, `hooks/`, `agents/`, `commands/`, `skills/`,
`tests/`, living capability specs, or `.claude-plugin/`. Later changes to a
proven surface require their own justified task and must retain existing
signatures/behavior; living specs change through sync. The 501-test suite and
11-pair sync check are compatibility tripwires throughout.

## Risks

- Ordinary plugin hooks are user-disableable and do not cover hosted/specialized
  tool paths.
- Codex hook APIs and collaboration tool names are alpha-versioned.
- A definition hash does not transitively authenticate handler source.
- Parent permission overrides can widen a nested custom agent's sandbox.
- Claude may be absent, unauthenticated, out of quota, or return contradictory
  structured fields.
- Additive Claude/Codex packaging can drift without shared contract vectors.
- An unsafe abstraction can hide host-specific dispatch and state behind a
  nominally shared policy API.
- A verify-then-import sequence can execute bytes other than the bytes whose
  digest was checked.
- Definition trust does not authenticate the host, interpreter, or trust store;
  these remain an explicit trusted computing base and readiness assumption.
- Parallel mutating agents can collide or alter the Owner checkout unless each
  writer is isolated by a separate fixed-root process and exclusive lease.
- A broad fail-closed hook matcher can brick unrelated/read-only tools after a
  host rename; matcher scope must be narrow and coverage explicit.
- A generated runtime can drift from policy sources unless deterministic
  byte-for-byte rebuild comparison runs in CI, not only at release.
- A standalone Codex package can drift from the authoritative project scaffold
  unless its deterministic scaffold bundle is rebuilt and compared in CI.
- Windows launcher discovery and quoting differ from POSIX.

## Rollback

The MVP is additive. Disable or uninstall the Codex plugin and remove
Codex-specific project scaffold files; the current Claude plugin and shared
SDD+ lifecycle remain intact. Do not migrate or delete existing Claude
packaging during this change.
