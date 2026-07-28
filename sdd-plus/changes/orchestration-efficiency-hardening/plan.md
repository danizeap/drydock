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
   request is packet-sized, not a source dump.
2. Define one deterministic candidate fingerprint from repository identity,
   base/head or dirty-diff digest, packet revision, and relevant configuration.
   It identifies evidence; it does not authenticate it.
3. Define phase envelopes for `plan_peer`, `mutation`, `cross_review`,
   `verification`, and `integration`: actual elapsed time, call count, input
   bytes, configured provider ceiling, known capacity snapshot, and stop
   action. Do not claim token counts the provider did not expose.
4. Correct the existing budget-ceiling failure classifier first, with a
   regression proving `return_to_owner`.
5. Add a single-flight invocation record keyed by candidate/request/model.
   A live matching process is attached to or reported; an automatic duplicate
   is forbidden. Terminal structured output is written atomically before the
   result is reported.
6. Add review-input preflight. Plan critique remains small. A source review
   above the configured byte envelope is rejected before spawn with routes:
   repository-aware Owner relay, approved digest-bound snapshot work, or scope
   reduction that still discloses omitted files.
7. Add proof records keyed by candidate fingerprint plus exact command and
   relevant environment fingerprint. Targeted checks run during mutation. A
   full suite runs once after freeze. Evidence-only commits reuse code proof;
   source changes invalidate the affected commands.
8. Update orchestration skill/operator guidance so normal work uses one
   mutator, one reviewer round at a time, one verifier, bounded retries, and a
   visible escalation when an envelope is exhausted.
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
- Durable invocation state could retain prompts or source. Store only bounded
  metadata, digests, and terminal structured results that pass the outbound
  policy.
- Attaching to a live process can become a denial of service. Every record has
  a bounded lease/process-identity check and a terminal timeout.
- Tight default budgets can make FULL work unusable. Exhaustion returns an
  explicit route, never a fabricated pass or silent downgrade.
- A repo-aware peer transport can widen confidentiality exposure. It remains
  out of the first slice unless separately designed and approved.

## Rollback

Keep the new evidence and phase-budget path behind a controller feature flag
until dogfood proves it. Rollback disables that flag and reverts the additive
module/contract changes; the corrected fail-closed budget classification
remains because it fixes an existing spec violation.
