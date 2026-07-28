# Spec Delta: claude-usage-signal

Capability: claude-usage-signal

## ADDED Requirements

### Requirement: Capacity awareness is automatic and dual-provider

Before producing a delegation allocation, Drydock SHALL automatically obtain
fresh Claude and Codex capacity snapshots without requiring the Owner to enter
usage values. Manual snapshots MAY exist for tests and diagnostics but SHALL
NOT satisfy production readiness for capacity-aware routing.
The private Claude path SHALL be disabled before broker process spawn and
credential access unless the Owner has explicitly enabled the reviewed
mechanism.

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
windows, window kind (`fixed_reset | sliding | unknown`), and enum limitation
codes. It SHALL reject unknown fields, non-finite or
out-of-range values, implausible timestamps, and any credential,
authorization header, account identifier, raw response, prompt, or repository
field.
Window names SHALL match `^[a-z0-9_]{1,32}$`; limitation values SHALL come from
a fixed code enum rather than provider-controlled text. All strings SHALL be
bounded and the broker plus core validator SHALL reject bearer/private-key
markers, known token prefixes, and high-entropy secret-shaped values.

#### Scenario: Broker returns a bearer token beside valid usage

- **WHEN** a provider response contains otherwise valid windows plus a token
- **THEN** the entire response is rejected and no portion is cached

#### Scenario: Provider returns a current sanitized snapshot

- **WHEN** all fields match the contract and the sample is within the freshness
  window
- **THEN** Drydock may use its remaining/reset values as scheduling evidence

### Requirement: Claude credentials are confined to a dedicated broker

The Claude broker SHALL be the only Drydock code path intentionally designed
to read Claude credentials. On Windows this is a same-user anti-accidental-flow
boundary, not OS isolation from a malicious same-user pilot, worker, or other
process; that residual trusted-computing-base limitation SHALL be reported.
The pilot, scheduler, logs, cache, packets, hooks, workers, and verifier SHALL
NOT receive, copy, store, or log Claude credentials or raw usage responses.
The broker SHALL expose a fixed bounded usage operation rather than arbitrary
network or credential access. It SHALL open credential state read-only, SHALL
NOT refresh, rotate, or write credentials, and SHALL report `unavailable` on
expiry or 401. Until a documented structured Claude source exists, use of the
observed private OAuth mechanism requires explicit Owner approval, Owner
acceptance of its private-endpoint permissibility risk, and a security-reviewed
implementation.

#### Scenario: Core asks for Claude capacity

- **WHEN** the scheduler invokes the broker
- **THEN** the broker receives no prompt, task, packet, or repository content
  and emits only the sanitized snapshot

#### Scenario: Broker cannot establish its credential boundary

- **WHEN** credential access, redaction, or the fixed request cannot be proven
- **THEN** Claude telemetry is `unavailable` and no token or partial response
  is returned

#### Scenario: Claude access token is expired

- **WHEN** the fixed usage request returns 401 or the read-only credential
  record is already expired
- **THEN** the broker reports `unavailable`, performs no refresh request, and
  does not modify the Claude credential container

### Requirement: Routing protects every overlapping window

The scheduler SHALL evaluate every current provider-defined window according
to its declared kind. Fixed-reset windows MAY use a reset horizon; sliding
windows MAY use only burn evidence collected over a sufficient same-window
span; unknown-kind windows SHALL NOT contribute positive margin arithmetic.
The scheduler SHALL account for current remaining capacity, recent compatible
burn evidence, confidence, and explicit capacity reserved for required
planning and cross-review. Until a quota-per-task unit bridge is separately
evidenced, routing SHALL be ordinal and recommendation-only. It SHALL NOT
compare providers using one raw headline percentage alone or claim that a
token-denominated task is cardinally affordable in a percentage-denominated
window.

#### Scenario: Claude weekly capacity is high but five-hour capacity is low

- **WHEN** the five-hour projected margin binds before the weekly window
- **THEN** the scheduler limits Claude allocation according to the five-hour
  window and shifts suitable work to Codex

#### Scenario: Codex has twice Claude's usable runway

- **WHEN** normalized reserve-adjusted margins show materially more Codex
  runway for the proposed task class
- **THEN** the recommendation allocates more suitable execution work to Codex
  while retaining Claude capacity required for peer review

#### Scenario: Fixed capacity window resets before the coding horizon

- **WHEN** a `fixed_reset` provider window resets sooner than the Owner's
  target horizon
- **THEN** projected burn uses the shorter reset horizon and the decision names
  that reset

#### Scenario: Provider window semantics are unknown

- **WHEN** a current window has kind `unknown`
- **THEN** it cannot add positive headroom or support a reset-horizon claim

### Requirement: Burn and task-cost learning remain evidence-bounded

Drydock MAY estimate provider/window burn from compatible normalized snapshot
deltas and MAY estimate task cost from actual per-call usage grouped by
provider, model, and enum task class. Every estimate SHALL carry sample count,
observation span, unit, and confidence. Shared Claude account deltas SHALL NOT
be represented as Drydock-specific, model-specific, or chat-specific
consumption unless separately proven. Token-denominated task history SHALL NOT
be converted to quota percentage without evidenced sole-client intervals and
an explicit confidence-bounded conversion. Cold start remains ordinal and low
confidence rather than inventing cardinal feasibility.

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
Sampling SHALL be serialized across local Drydock instances through a
machine-local lease. A persistent minimum interval and per-day call cap SHALL
survive process restarts. The Windows parent SHALL establish a kill-on-close
Job Object before broker execution, drain stdout/stderr without pipe deadlock,
enforce a byte bound and timeout, and pin UTF-8 JSON handling. Failure to
establish those mechanics SHALL make the provider unavailable.

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

#### Scenario: Concurrent repositories request Claude capacity

- **WHEN** another Drydock instance holds the current machine-local sampling
  lease or the persistent call budget is exhausted
- **THEN** no second private-endpoint request starts and the caller receives
  current bounded cache evidence or `unavailable`

### Requirement: MVP recommendations require pilot review

The MVP scheduler SHALL emit a recommendation only. Required reserves SHALL be
structurally unavailable to worker allocation, stale snapshots SHALL be a
distinct type that cannot contribute headroom, and the pilot SHALL review the
recommendation before any worker dispatch. Enabling automatic capacity
collection SHALL NOT enable automatic side-effect dispatch.

#### Scenario: Recommendation would consume review reserve

- **WHEN** a candidate split requires capacity reserved for peer review or
  verification
- **THEN** that split is infeasible and is not emitted as a selectable or
  merely lower-ranked alternative
