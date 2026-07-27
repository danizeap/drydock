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
5. Score candidate task allocations against every overlapping window.
6. Select an auditable allocation that preserves the configured coding horizon.
7. Re-sample after material batches and revise the remaining allocation.
8. Continue on the available provider when the other is exhausted without
   claiming missing peer convergence.

## 4. MVP Scope

- Automatic Codex collection through `account/rateLimits/read`.
- An automatically invoked Claude usage broker in the Drydock installation.
- One normalized schema for all named capacity windows and reset times.
- Short-lived caching, backoff, freshness, and circuit breaking.
- Conservative account-burn estimates and task-cost defaults.
- Configurable reserves for flagship planning and review.
- An automatic allocation recommendation before each delegation batch.
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

## 6. System Components

- `CodexCapacityProvider`: reads Codex app-server rate limits.
- `ClaudeUsageBroker`: the only credential-owning component; returns sanitized
  Claude windows over a bounded local protocol.
- `SnapshotNormalizer`: strict schema/range/time/source validation.
- `CapacityCache`: short-lived current and explicitly stale snapshots.
- `BurnEstimator`: rolling provider/window utilization deltas.
- `TaskCostEstimator`: actual usage grouped by provider, model, and task class,
  plus confidence/sample count.
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
  "freshness_seconds": 12,
  "attribution": "shared_account",
  "windows": [
    {
      "name": "five_hour|seven_day|provider_named",
      "utilization_percent": 61.5,
      "resets_at": "ISO-8601 UTC or null"
    }
  ],
  "limitations": ["account-wide; not task-attributable"]
}
```

The routing result additionally records the target horizon, reserve per
provider/window, projected burn, binding window, task-cost estimate and
confidence, selected allocation, and rejected alternatives.

Unknown fields are rejected at the broker boundary. Tokens, account
identifiers, request headers, raw bodies, prompts, and repository content are
forbidden outside the credential-owning broker.

## 8. Data Flow

Codex app-server -> Codex provider -> normalization.

Claude credential store -> isolated broker -> private/official usage source ->
sanitization -> normalization.

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
lookup, token refresh, response parsing, and redaction are fixed inside the
broker.

## 10. Auth & Permissions Assumptions

Automatic Claude telemetry requires a credential-owning trusted component
until an official structured command exists. That component is part of
Drydock's trusted computing base and must be named honestly. Process isolation
prevents accidental token flow into the model-facing core; it is not a claim
that bundled broker code is outside Drydock as a product.

The first real credential-store probe requires explicit Owner approval after
the exact path/store, fields, access mode, logging, and network request are
shown. The broker requests no repository or tool-execution authority.

## 11. External Services / Integrations

- Codex app-server `account/rateLimits/read`.
- Claude Code's local credential store, exact Windows mechanism still to be
  probed with approval.
- Preferred future source: a documented Claude structured usage command.
- Current observed fallback candidate:
  `GET https://api.anthropic.com/api/oauth/usage` with
  `anthropic-beta: oauth-2025-04-20`.

The public widget proves the fallback mechanism can expose `five_hour`,
`seven_day`, and optional weekly Opus data. It also refreshes credentials,
which is why the broker requires a dedicated security review rather than being
copied into the pilot.

## 12. Scheduling Model

For each provider window:

- `remaining = 100 - utilization`
- `allocatable = max(0, remaining - reserve)`
- `horizon = min(owner_target_hours, hours_until_reset)` when reset is known
- `projected_burn = burn_rate * horizon`
- `margin = allocatable - projected_burn`

The provider's binding window is its lowest margin. A task allocation is
eligible only when projected task cost keeps all known margins non-negative.
Scores then consider:

- relative binding-window margin across Claude and Codex;
- task/model suitability and epistemic value;
- learned task cost and confidence;
- reserve needed for mandatory peer planning/review;
- cost of losing cross-model diversity;
- reset proximity, so capacity expiring soon may be spent before scarcer
  long-window capacity when quality is comparable.

Cold start uses conservative task bands rather than invented precision. Low
confidence widens estimated cost upward. Shared-account Claude burn includes
human and other-client activity, which is appropriate for protecting capacity
even though it cannot attribute a particular task.

## 13. Failure and Degraded Modes

- Claude exhausted, Codex available: Codex continues in `single_pilot`, with
  peer convergence not established.
- Codex constrained, Claude available: preserve Codex pilot/control capacity
  and shift suitable bounded work to Claude.
- One telemetry source stale/unavailable: do not infer headroom; protect the
  unknown provider, run a bounded operational probe if useful, and route with
  a visible degraded-confidence result.
- Both telemetry sources unavailable: continue governance but do not claim
  quota-optimized delegation.
- Broker schema/credential/endpoint failure: circuit-break the broker, retain
  only explicitly stale last-good display evidence, and never fail open.

## 14. Implementation Phases

1. Claude peer review and Owner-approved Windows credential-store probe.
2. Strict normalized snapshot types and fake providers.
3. Codex provider using the existing app-server mechanism.
4. Least-privilege Claude broker with private endpoint behind a feature flag
   and an official-command replacement seam.
5. Cache, history, backoff, and burn/task-cost estimators.
6. Reserve policy and allocation engine in recommendation-only mode.
7. Dogfood shadow decisions against human task splits.
8. Enable automatic allocation after accuracy and reserve preservation are
   verified; retain pilot audit before side effects.

## 15. Testing Strategy

- Snapshot tests for unknown/forbidden fields, timestamps, ranges, duplicates,
  stale/future samples, and provider-defined windows.
- Broker tests for credential redaction, fixed requests, timeout, response-size
  bounds, 401 refresh behavior, 429 `Retry-After`, backoff, and circuit break.
- Scheduler table/property tests over conflicting five-hour/weekly margins,
  asymmetric resets, exhausted providers, unknown windows, and reserves.
- Tests proving low-confidence costs are conservative and required peer
  reserves cannot be allocated to workers.
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

PASS WITH OPEN QUESTIONS. Automatic dual-provider awareness and smart
delegation are now mandatory MVP behavior. Implementation remains BLOCKED
until Claude peer review and explicit approval of the first real Windows
credential-store probe.
