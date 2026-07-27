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
absolute. A public menu-bar project demonstrates that a credential-bearing
local process can call Anthropic's private OAuth usage endpoint. That does not
make the endpoint documented or stable. Automatic behavior nevertheless means
some explicitly trusted component must obtain Claude telemetry until Anthropic
exposes a supported structured command.

## Scope

In scope:

- Automatic Claude and Codex usage collection before delegation decisions.
- A dedicated Claude usage broker that owns credential access while the pilot,
  scheduler, logs, and packet artifacts receive only sanitized capacity data.
- A provider-neutral, normalized snapshot contract for overlapping usage
  windows, resets, freshness, source, attribution, and limitations.
- A scheduler that compares binding runway across both providers, preserves
  peer/review reserves, and emits an auditable delegation recommendation.
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

## Acceptance Criteria

- [x] Automatic dual-provider awareness is a mandatory MVP property.
- [x] Manual values are diagnostic fixtures only, not normal routing input.
- [x] The pilot receives normalized capacity evidence without receiving
  credentials or raw provider responses.
- [x] The scheduler accounts for overlapping five-hour/weekly windows, reset
  timing, recent burn, task cost, and reserved peer/review capacity.
- [x] Missing, stale, malformed, or unknown evidence remains `unavailable`.
- [x] A recommendation names its evidence, confidence, reserves, and binding
  provider window; it never silently allocates from absent evidence.
- [x] The broker boundary and one-install requirement are explicit.
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
- Will Anthropic expose a documented structured usage command or API that can
  replace the private broker path?
- Which quota windows are actually returned for this subscription, and do
  Opus/Fable share or separate any provider-defined window?
- How many real task samples are needed before learned task-cost estimates may
  replace conservative defaults?
