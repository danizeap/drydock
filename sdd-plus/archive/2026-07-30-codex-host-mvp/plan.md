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

## Operational-Core Security Closeout

The Codex operational core is not complete while LaunchGuardian remains
point-in-time prose evidence beside the workflow. Reopen this packet in place;
do not create a competing packet or plan.

Goal: make the existing Codex controller admit integration or push only after a
candidate-bound LaunchGuardian review passes.

Components touched:

- `orchestration_control.py` gains one `security_review` phase between proof
  and independent verification and requires that phase for mutating workflows.
- `process_runner.py` owns the fixed LaunchGuardian invocation, process-tree
  cleanup, fresh committed-tree materialization, strict report parsing, and
  exact candidate binding.
- `orchestration_evidence.py` owns the bounded, user-writable security evidence
  record and its structural acceptance checks.
- The Codex orchestration skill and focused tests expose the same phase order
  and fail-closed behavior.

Data flow:

1. Cross-review accepts one exact isolated candidate.
2. The full required proof runs on that candidate. Official workflow execution
   refuses intermediate scope before spawn, and the controller reloads the
   keyed zero-exit, non-timeout `full_required_suite` record before it may
   advance.
3. The controller issues a candidate-bound `security_review` admission.
4. The runner materializes the exact commit outside the working checkout and
   invokes `launchguardian scan --target <fresh-root> --framework-mode
   --strict-scanners --output-dir <runner-owned-temp>`.
5. The runner reads a bounded regular JSON report once and records the report,
   observed LaunchGuardian launcher digest/reported version, exact command
   contract, candidate commit, executable fingerprint, and scanner statuses in
   durable workflow evidence. It recomputes all report aggregates from the
   actual finding rows instead of trusting count labels.
6. Only `APPROVED` or `APPROVED_WITH_DISPOSITIONS`, valid LGF configuration,
   zero open blocking findings, and all five expected scanners reporting
   `ran` may pass. Finding source/status values must belong to LaunchGuardian's
   documented 0.2.0 domains; invented values are malformed even when aggregate
   counts are recomputed around them. Missing tools, disabled/skipped/failed
   scanners, timeout, malformed output, stale identity, or another status is
   non-green.
7. `workflow-finish` independently reloads keyed evidence for every security
   outcome and refuses a caller classification that differs from the recorded
   result. A pass additionally requires the raw report; a procedural retry
   additionally requires a keyed failure-stage/process/liveness record. Both
   bind the consumed admission, objective, plan, mechanism, prior gates,
   candidate, age, and unchanged Owner checkout. The runner passes measured
   liveness and checkout equality into that record, and the store rejects a
   failure stage that contradicts its process facts.
8. Independent verification, integration, and optional push remain downstream.

Permissions and trust: LaunchGuardian is pointed at a fresh materialization and
instructed to write its report to a runner-owned temporary directory. The
native process is not host-filesystem write-confined; the runner detects a
changed Owner checkout after the process exits but does not claim prevention.
The local operating system, selected Python environment, `PATH`, scanner
executables, LaunchGuardian installation, controller state, and user-writable
evidence remain part of the disclosed trusted computing base. The observed
launcher digest and evidence provide identity and coordination, not
hostile-user authentication or toolchain provenance attestation.

Failure behavior: a substantive security finding invalidates the candidate and
returns to mutation. A procedural scanner failure may retry only
`security_review`, only while a keyed procedural record proves the exact
candidate and prior-gate digests remain unchanged. Process-tree termination
and the final output-pipe drain are independently bounded. No missing or failed
scan is converted into PASS.

Testing strategy: prove the happy path plus wrong-candidate, missing executable,
timeout, malformed report, invalid LGF, missing/disabled/failed scanner, open
blocker, aggregate reassignment, stale evidence, replayed admission,
caller-result reclassification, bounded post-timeout drain, and
substantive-versus-procedural resume behavior. Focused tests run before any
full suite or peer call.

Non-goals for this slice: publishing LaunchGuardian, changing its companion
repository, archiving either active Drydock packet, releasing Drydock, or
pushing any branch.

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
