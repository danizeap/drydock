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
   installation. The broker is a separate least-privilege process and is the
   only Drydock component allowed to access Claude authentication. It emits
   one sanitized snapshot; tokens and raw responses never cross its stdout
   boundary.
3. Prefer a future documented Claude structured usage command when available.
   Until then, the broker may use the observed private OAuth mechanism only
   after the Owner approves its exact credential-store access and the
   implementation passes security review.
4. Normalize both providers into named windows with utilization, reset time,
   freshness, source, and attribution. Preserve unknown provider-defined
   windows by safe name; never invent Fable/Opus semantics.
5. Sample automatically before plan negotiation/delegation, after a material
   execution batch, and before cross-review/verification. Cache briefly,
   respect `Retry-After`, and use exponential backoff/circuit breaking rather
   than frequent polling.
6. Maintain a non-sensitive rolling history of normalized utilization deltas
   and actual per-call usage metadata. Estimate:
   - account-wide burn per provider/window;
   - task cost by provider, model, and task class;
   - confidence/sample count for each estimate.
7. For every provider window compute remaining headroom after configured
   reserves and projected burn until the earlier of the target coding horizon
   or reset. The lowest margin is that provider's binding window.
8. Allocate a proposed task graph to maximize useful work while keeping every
   known binding window non-negative and preserving flagship capacity for
   required plan negotiation and cross-review. Prefer the provider with more
   normalized runway, not merely the larger raw percentage.
9. Return an auditable routing decision containing snapshots, binding windows,
   reserves, task-cost estimates, confidence, allocation, and rejected
   alternatives. The pilot reviews it before dispatch.
10. Treat stale or absent evidence conservatively. The scheduler may run a
    bounded operational probe, but SHALL NOT translate unknown capacity into
    positive headroom. If one provider is exhausted, continue governed work on
    the other; if telemetry is unavailable, report degraded routing rather
    than pretend optimization.
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
  when tokens never reach the core scheduler.
- Shared-account Claude deltas include other chats and clients; they estimate
  available runway but cannot prove Drydock-specific consumption.
- Raw percentages are not comparable when window lengths and resets differ.
- Cold-start task-cost estimates can create false precision; defaults and
  confidence must remain visible.
- Polling can trigger rate limits; stale last-good data can misroute work.
- An automatic scheduler can overfit cost and underweight epistemic value.
  Required peer/review reserves remain policy, not an optimization suggestion.

## Stop Conditions

Stop before implementation if tokens can reach the pilot or logs, if manual
input is presented as automatic telemetry, if unknown capacity becomes
positive headroom, if overlapping windows are collapsed into one percentage,
if the scheduler can waive governance, or if an undocumented endpoint is
described as supported.

## Rollback

This packet changes design only. A future implementation must make the broker
and automatic scheduler feature-gated so they can fail closed to degraded
routing without disabling Drydock lifecycle governance.
