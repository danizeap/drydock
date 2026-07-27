# Spec Delta: claude-usage-signal

Capability: claude-usage-signal

## ADDED Requirements

### Requirement: Capacity awareness is automatic and dual-provider

Before producing a delegation allocation, Drydock SHALL automatically obtain
fresh Claude and Codex capacity snapshots without requiring the Owner to enter
usage values. Manual snapshots MAY exist for tests and diagnostics but SHALL
NOT satisfy production readiness for capacity-aware routing.

#### Scenario: Both providers have current telemetry

- **WHEN** the pilot prepares a task split
- **THEN** the routing decision uses current normalized Claude and Codex
  windows, not a fixed provider ratio

#### Scenario: Only manual values are available

- **WHEN** no automatic provider has produced a fresh snapshot
- **THEN** readiness reports automatic capacity routing unavailable

### Requirement: Usage providers expose only sanitized snapshots

The core scheduler SHALL accept capacity evidence only through a strict,
versioned, provider-neutral snapshot containing provider, source, status,
sampled time, freshness, shared-account attribution, named utilization/reset
windows, and limitations. It SHALL reject unknown fields, non-finite or
out-of-range values, implausible timestamps, and any credential,
authorization header, account identifier, raw response, prompt, or repository
field.

#### Scenario: Broker returns a bearer token beside valid usage

- **WHEN** a provider response contains otherwise valid windows plus a token
- **THEN** the entire response is rejected and no portion is cached

#### Scenario: Provider returns a current sanitized snapshot

- **WHEN** all fields match the contract and the sample is within the freshness
  window
- **THEN** Drydock may use its remaining/reset values as scheduling evidence

### Requirement: Claude credentials are confined to a dedicated broker

The Claude broker SHALL be the only credential-owning Drydock component. The
pilot, scheduler, logs, cache, packets, hooks, workers, and verifier SHALL NOT
receive, copy, store, or log Claude credentials or raw usage responses. The
broker SHALL expose a fixed bounded usage operation rather than arbitrary
network or credential access. Until a documented structured Claude source
exists, use of the observed private OAuth mechanism requires explicit Owner
approval and a security-reviewed implementation.

#### Scenario: Core asks for Claude capacity

- **WHEN** the scheduler invokes the broker
- **THEN** the broker receives no prompt, task, packet, or repository content
  and emits only the sanitized snapshot

#### Scenario: Broker cannot establish its credential boundary

- **WHEN** credential access, redaction, or the fixed request cannot be proven
- **THEN** Claude telemetry is `unavailable` and no token or partial response
  is returned

### Requirement: Routing protects every overlapping window

The scheduler SHALL evaluate every current provider-defined window and SHALL
use the lowest reserve-adjusted projected margin as that provider's binding
window. It SHALL account for remaining capacity, time to reset, recent burn,
estimated task cost, estimate confidence, and explicit capacity reserved for
required planning and cross-review. It SHALL NOT compare providers using one
raw headline percentage alone.

#### Scenario: Claude weekly capacity is high but five-hour capacity is low

- **WHEN** the five-hour projected margin binds before the weekly window
- **THEN** the scheduler limits Claude allocation according to the five-hour
  window and shifts suitable work to Codex

#### Scenario: Codex has twice Claude's usable runway

- **WHEN** normalized reserve-adjusted margins show materially more Codex
  runway for the proposed task class
- **THEN** the recommendation allocates more suitable execution work to Codex
  while retaining Claude capacity required for peer review

#### Scenario: Capacity will reset before the coding horizon

- **WHEN** a provider window resets sooner than the Owner's target horizon
- **THEN** projected burn uses the shorter reset horizon and the decision names
  that reset

### Requirement: Burn and task-cost learning remain evidence-bounded

Drydock MAY estimate provider/window burn from normalized snapshot deltas and
MAY estimate task cost from actual per-call usage grouped by provider, model,
and task class. Every estimate SHALL carry sample count/confidence. Shared
Claude account deltas SHALL NOT be represented as Drydock-specific,
model-specific, or chat-specific consumption unless separately proven. Cold
start and low confidence SHALL use conservative upper estimates.

#### Scenario: Other Claude clients consume capacity

- **WHEN** account utilization rises between Drydock calls
- **THEN** the scheduler treats the rise as shared-account burn for runway
  protection but does not attribute it to a Drydock task

#### Scenario: Task class has insufficient history

- **WHEN** fewer than the required samples exist
- **THEN** routing uses a conservative default cost and reports low confidence

### Requirement: Telemetry and scheduling are bounded and non-authoritative

Collection SHALL occur automatically at routing decision points, after
material batches, and before review gates, with bounded execution, response
size, cleanup, cache freshness, backoff, and circuit breaking. Missing, stale,
malformed, future-dated, or failed evidence SHALL NOT become positive
headroom. Usage state SHALL NOT authorize tools, waive packet/release gates,
or establish peer convergence.

#### Scenario: Provider hangs or emits oversized output

- **WHEN** collection exceeds its time or size limit
- **THEN** Drydock terminates the supported process boundary, records the
  provider as unavailable, and does not parse a partial snapshot

#### Scenario: One provider is exhausted

- **WHEN** one provider has no allocatable reserve-adjusted capacity and the
  other has current usable capacity
- **THEN** governed work may continue on the available provider while the
  result states the lost peer/diversity evidence

#### Scenario: Telemetry is stale

- **WHEN** the last valid snapshot exceeds its freshness window
- **THEN** it may be displayed only as stale and contributes no positive
  routing headroom
