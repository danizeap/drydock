# Brief

## Change

orchestration-efficiency-hardening

## User Need

Meaningful Drydock work must finish quickly enough to remain useful without
trading away plan critique, independent verification, deterministic guards, or
honest evidence. The Owner needs the orchestrator to notice model capacity,
elapsed time, duplicate work, and oversized review inputs automatically.

## Problem

The adaptive-ledger dogfood run consumed about an hour and, by the Owner's
observed account gauge, roughly 11 percent of weekly Codex capacity. The work
was genuinely FULL, and the governance caught real defects, but the execution
was wasteful:

- architectural peer review arrived after implementation and forced redesign;
- flagship workers repeatedly loaded broad repository context;
- full suites were repeated after review-driven changes;
- duplicate verifier work was briefly active;
- peer review embedded 297 KB of code because the bounded peer had no
  repository-read capability;
- Opus 5 and Fable 5 each consumed their $1 call ceiling without a verdict;
- an outer command timeout orphaned the first peer process and lost its output;
- `error_max_budget_usd` incorrectly returned `continue_codex_only`, despite the
  peer-unavailable spec requiring budget violations to return to the Owner.

The framework has proportional modes but no executable per-phase work budget,
candidate fingerprint, proof-reuse contract, or duplicate-work guard.

The later Codex-host dogfood exposed a second, more fundamental efficiency
failure. A one-line, 1,255-byte documentation insertion accumulated a
505-line plan, 528 lines of negotiation evidence, nine recorded Claude calls,
and no integrated result. Individual guards failed closed, but the pilot
manually coordinated independent controller commands and repeatedly created
new procedural blockers. There is no single machine-owned workflow, no
structured authority-to-plan preflight, no objective-level circuit breaker
across closed runs, and no unique current-plan pointer. Safe refusal without a
bounded route to progress is not an acceptable operating result.

## Scope

In scope:

- Replace peer-failure classification with a fail-closed allowlist: only known
  benign availability failures may enter single-pilot; every unknown subtype
  returns to the Owner.
- Require architecture/security peer critique before mutation for FULL changes
  that objectively affect persistence, permissions, process boundaries, or
  verification semantics, regardless of how the packet labels itself.
- Partition executable-surface and packet-evidence fingerprints so unchanged
  executable proof can be identified without evidence-recording regress.
- Add a targeted-to-full test ladder: targeted checks while the candidate
  changes, one full pass after freeze, and selective reruns after
  evidence-only or isolated corrections.
- Add explicit per-phase and cumulative per-run envelopes for elapsed time,
  model calls, input bytes, and provider budget. Unknown token/usage data
  remains unknown.
- Reject an oversized peer payload before provider spend and route it to a
  repository-aware/manual review or a separately approved snapshot mechanism.
- Persist peer invocation identity and screened, bounded terminal output
  outside the repository with logical expiry at 24 hours and deletion on the
  first later read/start, so an outer-shell interruption cannot silently invite
  a duplicate call.
- Record dogfood efficiency with observable counts and timings, not fabricated
  token savings.
- Replace manual pilot choreography with one deterministic workflow state
  machine whose transitions are locally validated before provider spend.
- Bind the workflow to one strict, structured Owner authority manifest. Peer
  models review technical correctness; they neither interpret nor grant
  side-effect authority.
- Preserve exactly one current structured plan revision per Owner objective,
  with explicit supersession lineage so stale plans remain auditable but cannot
  satisfy a current gate.
- Add an objective-level circuit breaker that survives run closure and cannot
  be reset by opening another run without both explicit Owner action and a
  material plan, authority, or controller change.
- Use compact delta review after the first peer round and keep reusable
  containment, proof, verification, and push controls in controller code rather
  than repeating them in every task plan.

Out of scope:

- Weakening independent verification, fail-closed gates, or required full
  acceptance proof.
- Building the future credential-owning Claude usage helper.
- Inventing a universal model-reliability score or routing calibration from one
  dogfood run.
- Giving the peer shell, write, web, MCP, or unrestricted repository tools.
- Implementing a general-purpose read-only repository snapshot server in the
  first slice.
- Release, installation, archive, or deployment.

## Acceptance Criteria

- [ ] Only an explicit allowlist of proven availability failures may continue
  single-pilot; budget, policy, refusal, context-limit, and every unknown or
  unmapped subtype return `return_to_owner`.
- [ ] A duplicate live invocation with the same candidate/request fingerprint
  is refused or attached to, never started again.
- [ ] FULL persistence/permission/process/verification changes trigger
  architecture critique objectively; a skipped critique is machine-readable
  and cannot satisfy convergence.
- [ ] Proof reuse requires a clean committed tree, a hard block on ignored
  Python/pytest injection paths, a fresh bytecode-free proof root, and exact
  executable-surface/command/environment binding; the final executable surface
  receives one complete required-suite run with no composed substitute.
- [ ] Oversized embedded review input is rejected before a provider call and
  produces an actionable route.
- [ ] Every phase reports actual elapsed time, calls, input bytes, and known
  capacity evidence; missing usage never becomes an estimate presented as
  fact.
- [ ] One durable run ID spans all invocations for the Owner objective and has
  a cumulative ceiling; separate runs are explicitly not presented as a weekly
  cap, only an explicit recorded Owner action can reset the run, and a cheaper
  post-exhaustion model cannot satisfy any gate.
- [ ] Durable peer results are secret-screened, size-bounded, fresh, retained
  for a bounded period, stored outside the repository, and never called
  authenticated evidence.
- [ ] The final workflow retains independent verification and all existing
  safety gates.
- [ ] One controller entry point owns preflight, peer planning, mutation,
  cross-review, proof, verification, integration, optional push, and terminal
  reporting; an invalid or skipped transition fails before its side effect.
- [ ] A schema-valid authority manifest is checked locally against the exact
  plan before any peer or worker process, and a plan cannot request paths,
  actions, branches, remotes, calls, time, bytes, or spend outside it.
- [ ] One objective has exactly one current plan revision. Superseded plans are
  identified as history and cannot satisfy current peer, mutation, proof,
  verification, integration, or push gates.
- [ ] Two procedural pre-worker failures, fifteen observed minutes without a
  worker, or $1.50 of observed peer spend without a worker opens the default
  circuit. A fresh run alone cannot close it.
- [ ] Later peer rounds receive the unresolved technical blockers and changed
  plan fields, not a replay of the complete workflow history.
- [ ] The Codex operating path uses one Owner-facing task or direct task
  coordination; manual Owner copy/paste relay is not the default transport.

## Impact Areas

- Backend: Codex orchestration controller, process/result handling, evidence
  fingerprints, and test routing.
- Frontend:
- Data model: bounded local orchestration-run evidence; no prompt or source
  bodies.
- API: structured phase/run envelope, executable/evidence fingerprints,
  proof-reuse decision, and corrected budget-failure workflow.
- AI/model behavior: earlier peer involvement, right-sized single-worker
  execution, no automatic duplicate calls.
- Documentation:
- Operations/security: process ownership, durable terminal capture, strict
  outbound byte budget, and unchanged authority boundaries.

## Open Questions

- Which conservative default phase envelopes should ship before enough
  dogfood evidence exists? The mechanism must support Owner configuration and
  report defaults honestly.
- Can the current controller persist only digests/metadata while still
  recovering a terminal peer result after invoker interruption?
- Which source changes invalidate which proof commands without creating an
  unsafe cache?
- What fixed retention interval and terminal-result byte cap are sufficient
  for recovery without turning orchestration state into a content archive?
