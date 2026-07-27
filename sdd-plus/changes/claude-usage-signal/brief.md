# Brief

## Change

claude-usage-signal

## Intake

Mode: FULL design-only packet. Primary skill: `architect`. The change concerns
an external account signal, an undocumented service endpoint, credential
ownership, and routing decisions. No implementation, credential access, token
refresh, or live Anthropic usage request is authorized by this packet.

## User Need

Give the Codex-hosted Drydock pilot enough honest capacity evidence to decide
when Claude is a sensible peer, when it should preserve the Owner's remaining
Claude time, and when it must continue in single-pilot mode.

## Problem

Drydock can prove whether Claude Code is authenticated and whether one bounded
peer call worked, but it cannot currently report remaining Claude capacity or
reset timing. The existing `pace_forecast` correctly returns `unavailable`
without all required inputs.

The prior statement that Claude has no programmatic usage source was too
absolute. A public menu-bar project demonstrates that a credential-bearing
local process can call Anthropic's private OAuth usage endpoint. That does not
make the endpoint documented, stable, credential-free, or automatically
acceptable for Drydock. The current blueprint expressly says Drydock never
reads, copies, stores, or logs Claude credentials.

## Scope

In scope:

- A provider-neutral, sanitized usage-snapshot contract.
- A credential-free Drydock boundary: providers return numbers, never tokens.
- A manual/external-broker MVP that can be useful before an official Claude
  structured usage command exists.
- Freshness, cache, backoff, validation, and advisory routing semantics.
- Honest limits around shared-account attribution and burn-rate inference.
- A decision record for the private OAuth mechanism discovered in the public
  widget and the installed Claude Code binary.

Out of scope:

- Reading Claude Code credential files, macOS Keychain items, Windows
  credential stores, process memory, browser sessions, or environment tokens.
- Calling `https://api.anthropic.com/api/oauth/usage`.
- Refreshing or writing Claude OAuth tokens.
- Shipping the public widget's authentication mechanism inside Drydock.
- Claiming that an undocumented endpoint or response schema is stable.
- Implementing automatic model selection or a routing policy in this packet.
- Claiming a Fable-specific quota window without observed evidence.

## Acceptance Criteria

- [x] The architecture distinguishes a machine-readable source from a
  credential-safe Drydock integration.
- [x] The snapshot contract contains only capacity, reset, source, freshness,
  attribution, and limitation fields.
- [x] Missing, stale, malformed, or unknown evidence remains `unavailable`.
- [x] Usage evidence is advisory and cannot authorize tools, skip gates, or
  establish peer convergence.
- [x] The private OAuth path remains outside the MVP and requires a separate
  Owner-approved credential-boundary change before implementation.
- [x] The blueprint identifies an implementable first version that does not
  require Drydock to read Claude credentials.
- [ ] Owner chooses whether a future credential-owning helper is acceptable.
- [ ] Claude peer reviews the architecture when usage returns.

## Impact Areas

- Backend: future provider interface and sanitized cache.
- Frontend: none in this packet.
- Data model: short-lived advisory snapshot; no credentials or raw response.
- API: local provider contract only; no public network API.
- AI/model behavior: future routing advice, never authority.
- Documentation: correct the absolute "no programmatic way" claim at spec-sync
  time without implying an official supported API exists.
- Operations/security: credential boundary, rate limiting, stale data, shared
  account attribution, and undocumented endpoint drift.

## Open Questions

- Will Anthropic expose a documented structured usage command or API?
- Should a future Owner-approved helper own credentials in a separate process,
  or should Drydock support only manual/external sanitized snapshots?
- Which windows are actually available for this subscription over time?
- What minimum sample history is sufficient for a useful burn-rate estimate?
