# Plan

## Change

claude-usage-signal

## Approach

This revision freezes the automatic scheduling architecture. It does not
authorize credential access or runtime implementation. The full design is in
`build-blueprint.md`.

1. Port the existing Codex `account/rateLimits/read` capability behind a
   normalized `CapacityProvider` interface.
2. Ship a dedicated Claude usage broker as part of the one-place Drydock
   installation. The broker is the only Drydock code path intentionally
   designed to read Claude authentication. On Windows it remains a same-user
   anti-accident boundary, not protection from a malicious same-user process.
   It opens the credential container read-only, never refreshes or writes it,
   and emits one sanitized snapshot; tokens and raw responses never cross its
   stdout boundary. Expired credentials or 401 yield `unavailable`.
3. Prefer a future documented Claude structured usage command when available.
   Until then, the broker may use the observed private OAuth mechanism only
   after the Owner approves its exact credential-store access and the
   implementation passes security review.
4. Normalize both providers into strictly named windows with utilization,
   `fixed_reset | sliding | unknown` kind, reset time only where semantically
   valid, one sampled timestamp, source, attribution, and enum limitation
   codes. Never invent Fable/Opus semantics or persist provider-controlled
   free text.
5. Sample automatically before plan negotiation/delegation, after a material
   execution batch, and before cross-review/verification. Cache briefly,
   respect `Retry-After`, and use exponential backoff/circuit breaking rather
   than frequent polling. A machine-local lease serializes shared-account
   sampling across repositories. A persistent minimum interval and per-day
   cap survive restarts; the feature flag is checked before broker spawn or
   credential touch.
6. Maintain a non-sensitive rolling history of normalized utilization deltas
   and actual per-call usage metadata. Estimate:
   - account-wide burn per provider/window;
   - task cost by provider, model, and enum task class in provider-reported
     units;
   - confidence/sample count for each estimate.
   Task-token history SHALL NOT be converted into quota-window percentage
   unless separately evidenced sole-client intervals establish that bridge
   with explicit confidence bounds.
7. For fixed-reset windows with sufficient observations, compute remaining
   headroom after reserves and conservatively projected burn until the earlier
   of the target horizon or reset. Sliding windows use only semantics supported
   by their observed span. Unknown-kind windows may reduce confidence or
   availability but never contribute positive arithmetic headroom.
8. Produce an ordinal proposed task split that preserves flagship capacity
   for required plan negotiation and cross-review. Prefer more suitable work
   on the provider with the stronger reserve-adjusted runway; do not claim a
   task is cardinally affordable until the unit bridge is evidenced.
9. Return an auditable routing decision containing snapshots, binding windows,
   reserves, task-cost estimates, confidence, allocation, and rejected
   alternatives. Reserve-waiving choices are structurally infeasible, not
   normalized as alternatives. The pilot reviews every recommendation before
   dispatch; automatic side-effect dispatch is not part of this MVP.
10. Treat stale or absent evidence conservatively. The scheduler may run a
    bounded operational probe that can only downgrade a source to `exhausted`
    or `unknown`, never produce or increase headroom, and remains subject to
    the same call budget and circuit breaker. If one provider is exhausted,
    continue governed work on the other; if telemetry is unavailable, report
    degraded routing rather than pretend optimization.
11. Test only with fake providers and recorded sanitized fixtures. No CI test
    reads credentials or calls Anthropic.

## Files Expected To Change

Design packet:

- `sdd-plus/changes/claude-usage-signal/brief.md`
- `sdd-plus/changes/claude-usage-signal/build-blueprint.md`
- `sdd-plus/changes/claude-usage-signal/evidence.md`
- `sdd-plus/changes/claude-usage-signal/specs/claude-usage-signal.md`
- packet task, decision, and verification records

Future implementation packet:

- a dedicated Claude broker module/process;
- normalized capacity-provider and snapshot types;
- automatic sampling/cache/history;
- cross-provider routing policy and CLI/readiness output;
- fake-provider and scheduler test suites.

## Risks

- The private Claude endpoint and credential storage can change without notice.
- A bundled credential broker expands Drydock's trusted computing base even
  when tokens never reach the core scheduler. Same-user Windows process
  separation is not an adversarial credential boundary.
- Shared-account Claude deltas include other chats and clients; they estimate
  available runway but cannot prove Drydock-specific consumption.
- Raw percentages are not comparable when window lengths and resets differ.
- Cold-start task-cost estimates can create false precision; defaults and
  confidence must remain visible.
- Polling can trigger rate limits; stale last-good data can misroute work.
- Concurrent Drydock instances can double-allocate shared headroom unless the
  machine-local admission lease is live and conservative.
- An automatic scheduler can overfit cost and underweight epistemic value.
  Required peer/review reserves remain policy, not an optimization suggestion.

## Stop Conditions

Stop before implementation if tokens can reach the pilot or logs, if the
broker can write or refresh Claude credentials, if manual
input is presented as automatic telemetry, if unknown capacity becomes
positive headroom, if overlapping windows are collapsed into one percentage,
if token cost is silently treated as quota percentage, if the scheduler can
waive governance or dispatch without pilot review, or if an undocumented
endpoint is described as supported or permitted without Owner acceptance.

## Rollback

This packet changes design only. A future implementation must make the broker
and automatic scheduler feature-gated so they can fail closed to degraded
routing without disabling Drydock lifecycle governance.
