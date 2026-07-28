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
2. Define one deterministic candidate fingerprint from repository identity and
   the complete clean committed Git tree. Dirty or untracked state disables
   proof reuse. Bind the relevant interpreter/tool/plugin/environment
   fingerprint separately and invalidate on any unknown relationship. The
   fingerprints identify evidence; they do not authenticate it.
3. Define phase envelopes for `plan_peer`, `mutation`, `cross_review`,
   `verification`, and `integration`, plus a cumulative run envelope: actual
   elapsed time, call count, input bytes, configured provider ceiling, known
   capacity snapshot, and stop action. Do not claim token counts the provider
   did not expose. A cheaper model after exhaustion may advise only; it cannot
   satisfy the exhausted gate.
4. Correct peer-failure classification first after plan convergence. Replace
   the catch-all continuation with an allowlist of known benign availability
   failures and regress an invented subtype to `return_to_owner`.
5. Add a single-flight invocation record keyed by candidate/request/model.
   A live matching process is attached to or reported; an automatic duplicate
   is forbidden. An expired lease without a terminal result returns to the
   Owner and never restarts automatically. Terminal structured output is
   secret-screened, capped at 64 KiB, written atomically outside the repository
   before it is reported, tagged with original observation time, and expires
   after 24 hours. A rejected result body leaves only bounded status and digest
   metadata.
6. Add review-input preflight. Plan critique remains small. A source review
   above the configured byte envelope is rejected before spawn with routes:
   repository-aware Owner relay, approved digest-bound snapshot work, or scope
   reduction that still discloses omitted files.
7. Add proof records keyed by candidate fingerprint plus exact command and
   relevant environment fingerprint. Targeted checks and composed evidence may
   accelerate intermediate work. After every tracked packet/source/evidence
   byte is frozen, the final complete required suite runs once against that
   exact fingerprint; no composed proof substitutes for this final pass.
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
- A repo-aware peer transport can widen confidentiality exposure. It remains
  out of the first slice unless separately designed and approved.

## Rollback

Keep proof reuse and phase-routing policy behind a controller feature flag
until dogfood proves them. Rollback disables that flag and reverts those
additive paths. The fail-closed peer classifier, duplicate-call single-flight,
out-of-tree result safety, and durable terminal capture remain enabled because
disabling them restores known governance or duplicate-spend defects.
