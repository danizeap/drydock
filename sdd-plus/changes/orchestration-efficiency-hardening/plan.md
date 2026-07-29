# Plan

## Change

orchestration-efficiency-hardening

## Active Plan State

- Revision: 2
- State: active
- Supersedes: revision 1 completion claim
- Canonical plan: this file only
- Reason: the Codex-host dogfood proved that the first slice hardened
  individual primitives but did not supply a usable end-to-end control plane.
  All revision-1 decisions and evidence remain historical input; no separate
  recovery plan is current.

## Approach

Execution mode: FULL because this changes privileged orchestration and the
conditions under which expensive proof is reused.

Primary skill: `architect` by routing definition. Its portable `SKILL.md` is
missing from this checkout, so the canonical framework protocol and
`drydock-orchestrate` are the disclosed fallback. Supporting skills during
implementation: backend for controller/process state and testing for negative
budget, duplicate-call, invalidation, and interruption cases.

1. Negotiate this architecture with Claude/Fable before runtime edits. The
   request is packet-sized, not a source dump. An Owner-relayed repository-aware
   review is an accepted peer route when the bounded adapter cannot return a
   verdict; the relay is recorded as such and grants no tool authority.
2. Partition deterministic fingerprints: an executable surface covers tracked
   source, tests, dependencies, configuration, generators, hooks, instructions,
   skills, specs, plans, and task contracts; an exact packet-evidence allowlist
   covers only schema-valid non-executable verification/review records.
   Dirty/untracked state or an ignored Python/pytest code-injection path
   disables reuse. Existing ignored bytecode caches in the Owner checkout do
   not: proof generation and reuse validation occur in a fresh root
   materialized from the exact executable commit, confirmed bytecode-free
   before spawn, with bytecode writes disabled. Tracked bytecode and unexplained
   bytecode in the proof root disable reuse. Bind interpreter/tool/plugin/
   environment separately and invalidate on any unknown relationship. None of
   these digests authenticates evidence.
3. Define phase envelopes for `plan_peer`, `mutation`, `cross_review`, `proof`,
   `verification`, `integration`, and optional `push`, plus a cumulative
   objective envelope that persists across every controller invocation, run
   ID, retry, and task turn for one Owner objective:
   actual elapsed time, call count, input bytes, configured provider ceiling,
   known capacity snapshot, and stop action. Do not claim token counts the
   provider did not expose or a weekly/cross-run ceiling. Only an explicit,
   recorded Owner action creates or supersedes the objective and resets the
   run. A cheaper model after exhaustion may advise only; it cannot satisfy any
   gate.
4. Correct peer-failure classification first after plan convergence. Replace
   the catch-all continuation with an allowlist of known benign availability
   failures and regress an invented subtype to `return_to_owner`.
5. Add a single-flight invocation record keyed by executable surface,
   request/model/schema/configuration, and run ID.
   A live matching process is attached to or reported; an automatic duplicate
   is forbidden. An expired lease without a terminal result returns to the
   Owner and never restarts automatically. Terminal structured output is
   secret-screened, capped at 64 KiB, written atomically outside the repository
   before it is reported and tagged with original observation time. It becomes
   ineligible after 24 hours; every read/start enforces expiry and deletes a
   stale body before returning metadata. A rejected result body leaves only
   bounded status and digest metadata.
6. Add review-input preflight. Plan critique remains small. A source review
   above the configured byte envelope is rejected before spawn with routes:
   repository-aware Owner relay, approved digest-bound snapshot work, or scope
   reduction that still discloses omitted files.
7. Add proof records keyed by executable-surface fingerprint plus exact command
   and relevant environment fingerprint. Targeted checks and composed evidence
   may accelerate intermediate work. After the executable surface freezes, the
   final complete required suite runs once against that exact fingerprint; no
   composed proof substitutes for this pass. Recording the result in an exact
   allowlisted evidence path changes only the packet-evidence fingerprint. The
   final report discloses the executable fingerprint and the exact
   packet-evidence-parent fingerprint that excludes the report being written,
   avoiding a self-referential digest.
8. Update orchestration skill/operator guidance and tested controller state so
   normal work has one active mutator per worktree, one peer/reviewer call per
   request fingerprint, and one verifier per final candidate. Disclose that
   the controller can measure its own subprocess calls and payloads but cannot
   observe all provider-side or nested-worker context ingestion.
9. Prove negative cases with fake provider/runner processes. Run focused tests
   while building, then one final adapter and legacy pass after the candidate
   freezes.
10. Add a strict structured authority manifest and compact structured technical
    plan. Validate both locally, require an immutable Owner-issued objective ID
    independent of editable plan prose, and prove every requested
    path/action/remote/branch and resource ceiling is a subset of Owner
    authority before provider spend. Bind the structured plan to the exact
    current bytes of this canonical packet `plan.md` and recheck that binding
    before each executor admission. Record each Owner-action digest in an
    out-of-tree one-time-use ledger; a digest used to create, supersede, resume,
    or resolve an objective cannot authorize another transition.
11. Add an out-of-tree objective workflow record with one current plan
    revision, explicit supersession lineage, an explicit success/failure/retry
    transition graph, and a controller-owned suspended or terminal state.
    Historical plans remain readable but cannot satisfy a current gate.
    Candidate, plan, authority, or mechanism changes invalidate their exact
    downstream gates. A blocked workflow records one permitted resume phase
    and requires a fresh, one-time Owner action before that phase can be
    re-admitted. The single workflow record is the atomic commit point; plan
    bodies are written before it, and every read fails closed if its referenced
    body is absent or digest-mismatched. Unreferenced bodies are inert orphans,
    not alternate current plans.
12. Add an objective-level circuit breaker across run IDs and the complete
    workflow, including cycles after mutation begins. Count cumulative phase
    entries, procedural/control failures, directly observed elapsed time,
    outbound bytes, and provider spend; worker start never clears or stops
    accumulation. Opening a new run does not reset the circuit. Closing it
    consumes a one-time Owner action bound to the exact opening-snapshot digest
    and requires a changed plan, authority scope, or controller mechanism
    digest. Preserve a monotonic resolution count; after the controller's hard
    maximum of one circuit resolution for an objective, another opening is
    terminal and only a newly Owner-issued objective ID with explicit
    predecessor lineage can proceed. Manifest thresholds may be lower but
    cannot exceed controller safety maxima. Report an unavailable provider-cost
    signal as unknown and keep every observable circuit axis active.
13. Make peer review technical-only. Round one receives the compact current
    plan and machine-generated control summary; later rounds receive stable
    blocker IDs, unresolved blockers, and changed fields. Authority or push
    bookkeeping failures are local preflight failures and consume no model
    call. Add `insufficient_context` as a non-converging technical verdict that
    names the exact bounded files, digests, or questions required. Truncation
    forces that verdict; it cannot produce convergence or be relabelled a
    procedural transport failure.
14. Add one workflow CLI surface that validates and advances the state machine.
    Each official peer, mutation, cross-review, proof, verifier, integration,
    and push wrapper must atomically validate and consume a short-lived,
    single-use admission record before its first expensive call or side effect.
    The record binds the immutable objective ID, workflow/run, phase, authority,
    plan, mechanism, input, exact prior gates, candidate when one exists,
    random nonce, and expiry. It is controller-enforced coordination inside the
    disclosed same-user, user-writable trusted computing base, not a signed
    hostile-user security boundary. Raw primitives remain callable by the
    Owner or same-user process but cannot advance or satisfy workflow gates.
    After a successful worker result, the official mutation wrapper rechecks
    the exact extracted snapshot and creates the clean isolated candidate
    commit itself; the worker never receives Git-metadata authority. The
    dedicated integration wrapper separately proves the unchanged clean Owner
    base and exact verified candidate, consumes its admission, performs only a
    fast-forward, and verifies the integrated v2 identity. An ambiguous
    integration result is terminal rather than automatically retried.
    Push stays unavailable until its dedicated wrapper enforces the strictest
    token, clean-tree, remote-baseline, exact-commit, and post-push checks.
15. Update operator guidance so one Owner-facing task or direct Codex task
    coordination is the normal route. Manual Owner relay is an explicit
    degraded fallback, never the default.
16. Dogfood the same frozen one-line documentation task only after focused
    controller tests pass. The task-specific plan must stay compact because
    standard safety behavior lives in the controller.
17. Replace the temporary environment-body transport fallback with a
    controller-owned out-of-tree payload file. Pass only its absolute path and
    expected SHA-256, require a regular non-link file under the state root,
    bound its size, read it once into memory, verify and parse that same buffer,
    recheck file identity, then delete it. Do not inherit the payload body into
    provider or worker environments.
18. Prove the complete retry graph, gate invalidation, one-time Owner actions,
    objective circuit, admission consumption, state crash recovery,
    insufficient-context verdict, payload transport, disabled feature-flag
    path, and honest unknown-cost reporting with negative tests before another
    end-to-end dogfood attempt.

## Files Expected To Change

- `adapters/codex/drydock/scripts/orchestrator.py`
- `adapters/codex/drydock/scripts/orchestration_control.py`
- `adapters/codex/drydock/scripts/orchestration_evidence.py` only where the
  existing run ledger must expose bounded state to the workflow controller.
- `adapters/codex/tests/test_orchestrator.py`
- `adapters/codex/tests/test_orchestration_control.py`
- Focused tests for any new evidence module.
- `adapters/codex/drydock/skills/drydock-orchestrate/SKILL.md`
- Relevant Codex operator documentation and generated scaffold bundle.
- This packet's delta spec and evidence.

## Risks

- Unsafe proof reuse could hide a regression. Default to invalidation whenever
  the changed surface or environment relationship is unknown.
- Durable invocation state could retain prompts or source. Never persist
  prompts/source; apply a separate at-rest content secret screen, 64 KiB result
  cap, 24-hour freshness/retention bound, and out-of-tree storage.
- Attaching to a live process can become a denial of service. Every record has
  a bounded lease/process-identity check and a terminal timeout.
- Tight default budgets can make FULL work unusable. Exhaustion returns an
  explicit route, never a fabricated pass or silent downgrade.
- A terminal result that exceeds 64 KiB or matches the at-rest secret screen is
  deliberately not recoverable and may require a new Owner-approved call. This
  fail-closed cost is disclosed rather than hidden through truncation.
- A repo-aware peer transport can widen confidentiality exposure. It remains
  out of the first slice unless separately designed and approved.
- Packet evidence is proof-neutral but can remain gate-relevant:
  `verification.md` does not invalidate executable proof, yet its parsed state
  still affects archive readiness and completion.
- Objective property detection is a pre-diff judgment. The controller can
  enforce the resulting FULL route, but cannot mechanically prove the human or
  model classified every objective correctly before mutation.
- The evidence store is user-writable, so its digests identify state but never
  authenticate or attest it.
- The capability still spans stacked, unsynced deltas until archive; explicit
  scenario supersession is required to avoid contradictory lineage.
- Structured authority is identifying controller input, not cryptographic proof
  that the Owner authored it. Codex host, task identity, and the pilot remain
  in the trusted computing base; the peer cannot strengthen that boundary.
- A circuit breaker that is too sensitive can stop valid technical iteration.
  Technical blockers do not increment the procedural-failure counter, but all
  attempts still consume cumulative objective time, byte, call, phase-entry,
  and observed-cost limits. One explicit bounded resolution prevents a local
  defect from permanently stranding the objective without permitting an
  unbounded reset loop.
- The workflow record and admission ledger are user-writable local coordination
  state. Random nonces prevent accidental replay by official executors but do
  not authenticate the Owner or resist a same-user process that edits state or
  invokes raw primitives. Drydock SHALL claim gate integrity only inside that
  trusted computing base.

## Rollback

Keep proof reuse and phase-routing policy behind a controller feature flag
until dogfood proves them. Rollback disables that flag and reverts those
additive paths. The fail-closed peer classifier, duplicate-call single-flight,
out-of-tree result safety, and durable terminal capture remain enabled because
disabling them restores known governance or duplicate-spend defects.
