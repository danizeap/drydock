# Build Blueprint: Automatic Cross-Provider Capacity Scheduler

## 1. Product Goal

Make the Codex-hosted pilot automatically aware of Claude and Codex capacity
so every task split protects useful coding time across five-hour and weekly
windows. This is an orchestration input, not a display feature.

## 2. Users

The Owner operating Drydock across repositories. The direct consumer is the
Codex pilot that plans and delegates work.

## 3. Core Workflows

1. Before dividing work, automatically collect Claude and Codex snapshots.
2. Validate and normalize every provider-defined window.
3. Update recent burn and task-cost estimates from sanitized history.
4. Reserve flagship capacity for negotiation and cross-review.
5. Rank candidate task allocations against compatible overlapping windows
   without converting task tokens into quota percentage.
6. Select an auditable ordinal recommendation that preserves configured
   reserves and requires pilot review before dispatch.
7. Re-sample after material batches and revise the remaining allocation.
8. Continue on the available provider when the other is exhausted without
   claiming missing peer convergence.

## 4. MVP Scope

- Automatic Codex collection through `account/rateLimits/read`.
- An automatically invoked Claude usage broker in the Drydock installation.
- One normalized schema for strictly named capacity windows with
  `fixed_reset`, `sliding`, or `unknown` semantics.
- Short-lived caching, backoff, freshness, and circuit breaking.
- Conservative account-burn estimates and task-cost defaults.
- Configurable reserves for flagship planning and review.
- An automatic recommendation before each delegation batch; no automatic
  side-effect dispatch in the MVP.
- Degraded routing when telemetry is unavailable.
- Fake-provider deterministic tests; no real credentials in CI.

Manual snapshots are test/diagnostic fixtures only. They do not satisfy the
MVP and cannot be presented as automatic awareness.

## 5. Non-Goals

- Showing a menu-bar dashboard.
- Exposing tokens or raw usage responses outside the broker.
- Exact Drydock-only attribution from shared-account Claude usage.
- Assuming an Opus, Fable, or other model-specific window from its name alone.
- Optimizing away required peer critique or independent verification.
- Hosted telemetry or a Drydock cloud credential store.
- Writing, refreshing, or rotating Claude credentials.
- Claiming same-user process separation is hostile-process credential
  isolation.
- Cardinal task affordability until quota-per-task units are evidenced.

## 6. System Components

- `CodexCapacityProvider`: reads Codex app-server rate limits.
- `ClaudeUsageBroker`: the only Drydock code path intentionally designed to
  read credentials; it opens them read-only and returns sanitized Claude
  windows over a bounded local protocol. On Windows this is an anti-accident
  boundary inside one user account, not hostile-process isolation.
- `SnapshotNormalizer`: strict schema/range/time/source validation.
- `CapacityCache`: short-lived current and explicitly stale snapshots.
- `BurnEstimator`: rolling provider/window utilization deltas.
- `TaskCostEstimator`: actual provider-reported usage grouped by provider,
  model, and enum task class, plus confidence/sample count. It does not convert
  tokens into quota-window percentage without a separately evidenced bridge.
- `ReservePolicy`: protects planning, cross-review, and Owner-configured runway.
- `AllocationEngine`: scores task/provider assignments across all windows.
- `RoutingAdvisor`: returns the selected allocation and evidence to the pilot.

## 7. Data Model Sketch

```json
{
  "schema_version": 1,
  "provider": "claude|codex",
  "source": "claude_broker|codex_app_server",
  "status": "current|stale|unavailable",
  "sampled_at": "ISO-8601 UTC",
  "attribution": "shared_account",
  "windows": [
    {
      "name": "five_hour|seven_day|provider_named_safe",
      "kind": "fixed_reset|sliding|unknown",
      "utilization_percent": 61.5,
      "resets_at": "ISO-8601 UTC or null"
    }
  ],
  "limitations": ["shared_account", "not_task_attributable"]
}
```

Window names match `^[a-z0-9_]{1,32}$`; limitation values come from a fixed
enum. Provider-controlled free text never enters the snapshot. The broker and
core validator both apply string bounds plus bearer/private-key, known-prefix,
and secret-shape rejection.

Freshness is a controller policy, not a provider-supplied snapshot field.
Within one process, age uses the monotonic receipt time. A future sample beyond
a two-second wall-clock skew is rejected. Persisted last-good snapshots become
display-only stale evidence after restart until a fresh automatic sample
arrives, so NTP jumps cannot create positive headroom.

The routing result additionally records the target horizon, reserve per
provider/window, compatible projected burn, binding evidence, task-cost unit
and confidence, selected recommendation, and rejected eligible alternatives.
Reserve-consuming candidates are infeasible and never appear as alternatives.

Unknown fields are rejected at the broker boundary. Tokens, account
identifiers, request headers, raw bodies, prompts, and repository content are
forbidden outside the credential-owning broker.

## 8. Data Flow

Codex app-server -> Codex provider -> normalization.

Claude credential store -> same-user anti-accident broker -> private/official
usage source -> sanitization -> normalization.

Normalized snapshots + rolling sanitized history + proposed task graph ->
reserve policy -> allocation engine -> auditable recommendation -> pilot ->
bounded workers. Actual call usage then updates task-cost history.

## 9. API / Interface Boundaries

The Claude broker is a separate least-privilege process shipped by the same
Drydock installation. It receives no prompt, packet, task, or repository
content. It emits exactly one size-bounded JSON snapshot on stdout. It must
never emit tokens or raw responses; stderr is fixed diagnostic codes, not
provider text.

The core scheduler has no credential-store access and cannot ask the broker to
make arbitrary network calls. Provider endpoint, method, header, credential
lookup, response parsing, and redaction are fixed inside the broker. Token
refresh and credential writes do not exist in the operation; expiry or 401
returns a fixed `unavailable` code.
The private raw response is validated against one pinned expected shape before
field extraction. Missing, extra, renamed, or differently typed fields return
the fixed `schema_drift` unavailable code; the broker never best-effort parses
a changed payload.

The parent evaluates a default-off feature flag before spawning the broker or
touching credential state. On Windows it creates the child suspended, assigns
it to a kill-on-close Job Object, then resumes it. Stdout and stderr are drained
asynchronously to avoid pipe deadlock; stdout is capped at 64 KiB of UTF-8 JSON
and stderr at 4 KiB of fixed diagnostic codes. Timeout, boundary-setup failure,
invalid UTF-8, CRLF ambiguity, oversize output, or descendant-cleanup
uncertainty yields `unavailable` with no partial parse.

## 10. Auth & Permissions Assumptions

Automatic Claude telemetry requires credential-reading trusted code until an
official structured command exists. That code is part of Drydock's trusted
computing base and must be named honestly. Same-user process separation reduces
accidental token flow into the model-facing core; it does not prevent the
pilot, workers, debuggers, crash tooling, or malware under the same Windows
principal from reaching the same user credential store.

The first real credential-store probe requires explicit Owner approval after
the exact path/store, redacted fields, read-only mode, logging, and absence of
network activity are shown. A later live private-endpoint call separately
requires Owner acceptance of the undocumented-endpoint permission/ToS risk.
The broker requests no repository or tool-execution authority and never writes
or refreshes the credential record.

## 11. External Services / Integrations

- Codex app-server `account/rateLimits/read`.
- Claude Code's local credential store, exact Windows mechanism still to be
  probed with approval.
- Preferred future source: a documented Claude structured usage command.
- Current observed fallback candidate:
  `GET https://api.anthropic.com/api/oauth/usage` with
  `anthropic-beta: oauth-2025-04-20`.

The public widget suggests that one observed version of the fallback mechanism
could expose `five_hour`, `seven_day`, and optional weekly Opus data. It does
not prove current availability or permission. Its credential refresh behavior
is deliberately excluded from Drydock because rotation could invalidate live
Claude Code clients.

## 12. Scheduling Model

For each compatible fixed-reset provider window:

- `remaining = 100 - utilization`
- `allocatable = max(0, remaining - reserve)`
- `horizon = min(owner_target_hours, hours_until_reset)` when reset is known
- `projected_burn = burn_rate * horizon`
- `margin = allocatable - projected_burn`

The provider's binding fixed-reset window is its lowest compatible margin.
Sliding windows require a sufficient same-window observation span; unknown
windows cannot contribute positive margin. Shared-account deltas may protect
runway but cannot become task attribution. Until separately evidenced
sole-client intervals establish percent-per-task-class units, task feasibility
is ordinal rather than cardinal. Scores then consider:

- relative binding-window margin across Claude and Codex;
- task/model suitability and epistemic value;
- learned task cost in its original unit and confidence, as suitability
  evidence rather than fabricated quota percentage;
- reserve needed for mandatory peer planning/review;
- cost of losing cross-model diversity;
- reset proximity, so capacity expiring soon may be spent before scarcer
  long-window capacity when quality is comparable.

Cold start uses conservative ordinal task bands rather than invented precision.
Shared-account Claude burn includes human and other-client activity, which is
appropriate for protecting capacity even though it cannot attribute a
particular task. A future cardinal bridge requires intervals that separately
prove sole-client activity, explicit sample/span thresholds, and confidence
bounds; it is not part of this MVP.
Provider adapters label a window `fixed_reset` or `sliding` only from
documented or directly evidenced provider semantics. Merely receiving a
`resetsAt` field is insufficient; otherwise the kind is `unknown`.

## 13. Failure and Degraded Modes

- Claude exhausted, Codex available: Codex continues in `single_pilot`, with
  peer convergence not established.
- Codex constrained, Claude available: preserve Codex pilot/control capacity
  and shift suitable bounded work to Claude.
- One telemetry source stale/unavailable: do not infer headroom; protect the
  unknown provider and route with a visible degraded-confidence result. A
  bounded operational probe may only downgrade the provider to `exhausted` or
  `unknown`; it never creates/increases headroom and shares the call budget and
  circuit breaker.
- Both telemetry sources unavailable: continue governance but do not claim
  quota-optimized delegation.
- Broker schema/credential/endpoint failure: circuit-break the broker, retain
  only explicitly stale last-good display evidence, and never fail open.
- Concurrent repositories: a machine-local lease admits one sampler; other
  instances consume a current bounded cache record or receive `unavailable`.
- Circuit-break state is Owner-visible in readiness, not only a log entry.

Capacity state lives outside repositories under the platform Drydock state
root (`%LOCALAPPDATA%\Drydock\capacity` on Windows). Reads reject symlinks,
reparse points, non-regular files, oversized records, unknown fields, and
non-canonical JSON. Records are user-writable evidence, not attestation.
Last-good display evidence is retained for at most 24 hours. A persistent call
ledger enforces a shipped hard floor of 300 seconds between private-endpoint
attempts and at most 96 attempts per rolling day across restarts; these
conservative defaults are uncalibrated and may only be tightened without a new
review.

## 14. Implementation Phases

1. Claude peer convergence and Owner-approved read-only Windows
   credential-schema probe.
2. Strict normalized snapshot types and fake providers.
3. Codex provider using the existing app-server mechanism.
4. Same-user anti-accident Claude broker with read-only credential access,
   private endpoint behind a default-off pre-spawn feature flag, pinned response
   schema, no refresh/write path, and an official-command replacement seam.
5. Cache, history, backoff, and burn/task-cost estimators.
6. Reserve policy and allocation engine in recommendation-only mode.
7. Dogfood shadow recommendations against human task splits, treating
   agreement as comparison rather than proof that the human split was correct.
8. Enable automatic recommendation after reserve preservation is verified;
   retain mandatory pilot review before every side effect. Automatic dispatch
   requires a separate future authorization and design.

## 15. Testing Strategy

- Snapshot tests for unknown/forbidden fields, value-shape/entropy rejection,
  enum limitation codes, timestamps, ranges, duplicates, stale/future samples,
  and fixed/sliding/unknown provider windows.
- Broker tests for credential redaction, fixed requests, timeout, response-size
  bounds, 401-without-refresh behavior, 429 `Retry-After`, backoff, persistent
  call caps, circuit break, Job Object cleanup, asynchronous pipe drain, and
  UTF-8/CRLF handling.
- Scheduler table/property tests over conflicting five-hour/weekly margins,
  asymmetric resets, exhausted providers, unknown windows, and reserves.
- Tests proving low-confidence costs are conservative and required peer
  reserves cannot be represented as allocatable to workers.
- Negative taint tests place unique synthetic canaries in fake credentials and
  raw provider bodies, then prove the canaries are absent from scheduler
  results, stdout/stderr, environment, state/cache records, packet artifacts,
  and every tested error path. This proves the covered sinks, not universal
  absence from OS crash dumps or a hostile same-user process.
- Cross-process tests prove one sampler across concurrent repositories and
  restart-surviving minimum-interval/per-day caps.
- Replay tests comparing proposed allocation with recorded sanitized dogfood
  sessions.
- No CI test reads credentials, calls Anthropic, or spends model quota.

## 16. LaunchGuardian Handoff and Next Skills

Before the broker ships, apply secrets/config hygiene, third-party integration,
dependency/supply-chain, privacy, logging, failure-mode, and AI-agent security
gates. Use `backend` for providers/scheduler, `mcp-ranger` for the credential
and app-server boundaries, and `testing` for adversarial broker and allocation
proof.

## Architecture Result

ROUND ONE NON-CONVERGED. Automatic dual-provider awareness remains mandatory,
but MVP routing is ordinal and recommendation-only until a cardinal unit bridge
is evidenced. Same-user broker separation is an anti-accident boundary, the
credential store is strictly read-only, and refresh is forbidden. Implementation
remains BLOCKED until Claude confirms the revised architecture and the Owner
explicitly approves the first read-only Windows credential-schema probe.
