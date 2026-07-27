# Spec Delta: claude-usage-signal

Capability: claude-usage-signal

## ADDED Requirements

### Requirement: Usage providers expose only a sanitized snapshot

Drydock SHALL accept Claude capacity evidence only through a strict,
versioned, provider-neutral snapshot containing source, status, sampled time,
freshness, shared-account attribution, named utilization/reset windows, and
limitations. It SHALL reject unknown fields, non-finite or out-of-range
values, implausible timestamps, and any credential, authorization header,
account identifier, raw response, or prompt field.

#### Scenario: Provider returns a bearer token beside valid usage

- **WHEN** a provider response contains otherwise valid windows plus a token
- **THEN** the entire response is rejected and no portion is cached

#### Scenario: Provider returns a current sanitized snapshot

- **WHEN** all fields match the contract and the sample is within the freshness
  window
- **THEN** Drydock may expose its remaining/reset values as advisory evidence

### Requirement: Drydock does not own Claude credentials

Drydock SHALL NOT discover, read, receive, copy, refresh, store, or log Claude
credentials. The first useful version SHALL use manual input or an external
local broker that owns its own authentication and emits only the sanitized
snapshot. Direct use of a private OAuth endpoint requires a separate,
Owner-approved credential-boundary change.

#### Scenario: No official structured usage command exists

- **WHEN** official feature detection finds no supported structured command
  and no approved external snapshot is available
- **THEN** usage status is `unavailable` rather than inferred from
  authentication, recent calls, or a private endpoint

#### Scenario: External broker owns a credential

- **WHEN** an Owner-approved broker returns a valid sanitized snapshot
- **THEN** Drydock may consume the snapshot without receiving or locating the
  broker's credential

### Requirement: Usage evidence is freshness-bounded and advisory

Missing, stale, malformed, future-dated, or provider-failed evidence SHALL be
reported as `unavailable`. A last-good snapshot MAY be displayed only with an
explicit stale status and age. Usage evidence SHALL NOT authorize tools,
waive packet or release gates, establish peer convergence, or prove
Drydock-specific/model-specific consumption.

#### Scenario: Cached usage exceeds its freshness window

- **WHEN** the last valid snapshot is older than its permitted freshness
- **THEN** routing does not treat its capacity as current or healthy

#### Scenario: Shared account changes between samples

- **WHEN** utilization rises between two valid samples
- **THEN** the delta may be described only as shared-account burn and not
  attributed to Drydock, Codex, Claude, Opus, Fable, or a particular chat

### Requirement: Provider execution and polling are bounded

External provider execution SHALL use bounded input, output, runtime, cleanup,
and response size. Polling SHALL occur at routing decision points with caching
and backoff, and SHALL respect a broker-reported retry interval. Deterministic
tests SHALL use fake providers and SHALL NOT read real credentials or call
Anthropic.

#### Scenario: Broker hangs or emits oversized output

- **WHEN** the provider exceeds its time or size limit
- **THEN** Drydock terminates the supported process boundary, records
  `unavailable`, and does not parse a partial snapshot as evidence
