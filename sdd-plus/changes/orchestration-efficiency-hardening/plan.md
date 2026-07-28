# Plan

## Change

orchestration-efficiency-hardening

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
3. Define phase envelopes for `plan_peer`, `mutation`, `cross_review`,
   `verification`, and `integration`, plus a cumulative run envelope that
   persists across every controller invocation/turn for one Owner objective:
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

## Files Expected To Change

- `adapters/codex/drydock/scripts/orchestrator.py`
- A small orchestration evidence module only if keeping the controller module
  bounded requires it.
- `adapters/codex/tests/test_orchestrator.py`
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

## Rollback

Keep proof reuse and phase-routing policy behind a controller feature flag
until dogfood proves them. Rollback disables that flag and reverts those
additive paths. The fail-closed peer classifier, duplicate-call single-flight,
out-of-tree result safety, and durable terminal capture remain enabled because
disabling them restores known governance or duplicate-spend defects.
