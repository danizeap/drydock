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
