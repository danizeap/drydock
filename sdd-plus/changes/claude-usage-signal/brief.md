# Brief

## Change

claude-usage-signal

## Intake

Mode: FULL architecture packet. Primary skill: `architect`. The change
concerns automatic external-account telemetry, an undocumented service
endpoint, credential ownership, and cross-provider delegation. No credential
access, token refresh, or live Anthropic usage request is authorized by this
design revision.

## User Need

Make Drydock automatically aware of both Claude and Codex capacity so the pilot
can divide planning, implementation, review, and verification work without
accidentally exhausting either provider's five-hour or weekly window. This is
resource-aware scheduling, not a usage dashboard.

## Problem

Drydock can prove whether Claude Code is authenticated and whether one bounded
peer call worked, but it cannot currently report remaining Claude capacity or
reset timing. Its existing `pace_forecast` correctly returns `unavailable`
without all required inputs. Codex rate-limit telemetry already has a
machine-readable app-server path, but it is not yet joined to Claude telemetry
or task allocation.

The prior statement that Claude has no programmatic usage source was too
absolute. A public menu-bar project suggests, from one observed implementation,
that a credential-bearing local process can call Anthropic's private OAuth
usage endpoint. That does not establish current availability, permission,
official support, or stability. Automatic behavior nevertheless means some
explicitly trusted component must obtain Claude telemetry until Anthropic
exposes a supported structured command.

## Scope

In scope:

- Automatic Claude and Codex usage collection before delegation decisions.
- A dedicated Claude usage broker that is the only Drydock code path
  intentionally designed to read Claude credentials, while the pilot,
  scheduler, logs, and packet artifacts receive only sanitized capacity data.
  On Windows this same-user process boundary limits accidental data flow; it
  is not isolation from a malicious or compromised same-user process.
- A provider-neutral, normalized snapshot contract for overlapping usage
  windows, resets, freshness, source, attribution, and limitations.
- A recommendation-only scheduler that compares conservative ordinal runway
  across both providers, preserves peer/review reserves, and emits an auditable
  delegation recommendation for pilot review before dispatch.
- Historical burn and task-cost estimates with conservative confidence.
- Freshness, cache, backoff, circuit-breaker, validation, and failure behavior.
- One Drydock installation; the broker may be a separate process boundary but
  is not a separately installed product.

Out of scope:

- Exposing Claude or Codex credentials to the model, pilot, scheduler, logs,
  cache, packet, or task subprocesses.
- Treating manual usage entry as a production delegation input.
- Claiming the private OAuth endpoint or its schema is an official contract.
- Exact Drydock-only attribution from account-wide Claude usage.
- Claiming a Fable-specific quota window without observed evidence.
- Letting usage state authorize tools, waive governance, or prove convergence.
- Writing, refreshing, rotating, or otherwise modifying Claude credentials.
- Cardinal conversion from per-call tokens to quota-window percentage without
  separately evidenced sole-client intervals and confidence bounds.
- Automatic side-effect dispatch based only on the scheduler's recommendation.

## Runtime Acceptance Criteria

These boxes remain unchecked until an implementation and its evidence exist.
They are requirements, not claims that the design packet already proves
runtime behavior.

- [ ] Automatic dual-provider awareness is a mandatory MVP property.
- [ ] Manual values are diagnostic fixtures only, not normal routing input.
- [ ] The pilot receives normalized capacity evidence without receiving
  credentials or raw provider responses.
- [ ] The scheduler accounts for provider-declared fixed, sliding, and unknown
  window semantics, recent burn, and reserved peer/review capacity without
  inventing a token-to-percentage conversion.
- [ ] Missing, stale, malformed, or unknown evidence remains `unavailable`.
- [ ] A recommendation names its evidence, confidence, reserves, and binding
  provider window; it never silently allocates from absent evidence.
- [ ] The broker's same-user anti-accident boundary and one-install requirement
  are explicit and verified without claiming hostile-process isolation.
- [ ] The broker opens Claude credential state read-only, never refreshes or
  writes it, and converts 401/expiry into `unavailable`.
- [ ] The feature is off before process spawn or credential touch unless the
  Owner explicitly enables the reviewed private-endpoint path.
- [ ] Claude peer reviews the architecture when usage returns.
- [ ] The Owner explicitly authorizes the first real Claude credential-store
  probe after reviewing the broker's exact access and logging behavior.

## Impact Areas

- Backend: automatic collectors, broker, normalized cache, scheduler.
- Frontend: readiness/status explanation only.
- Data model: short-lived capacity snapshots and non-sensitive routing history.
- API: bounded local broker protocol and internal scheduler result.
- AI/model behavior: automatic task allocation recommendations.
- Documentation: replace the absolute "no programmatic way" claim during spec
  sync and document the new credential-owning trusted component honestly.
- Operations/security: credential access, private endpoint drift, rate limits,
  stale data, shared-account attribution, and least-privilege process design.

## Open Questions

- What exact credential store and token-rotation behavior does Claude Code
  2.1.173 use on this Windows host? This requires a separately authorized
  read-only probe.
- Does Anthropic permit automated polling of this private endpoint with
  subscription credentials? This is an Owner acceptance decision, not a fact
  inferred from technical reachability.
- Will Anthropic expose a documented structured usage command or API that can
  replace the private broker path?
- Which quota windows are actually returned for this subscription, and do
  Opus/Fable share or separate any provider-defined window?
- What sole-client evidence, if any, could justify a bounded percent-per-task
  estimate? Until then, task cost remains ordinal and recommendation-only.
