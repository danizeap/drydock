# Build Blueprint: Claude Usage Signal

## 1. Product Goal

Give the Codex-hosted pilot an honest, low-trust signal about remaining Claude
capacity and reset timing so it can protect the Owner's useful coding pace.

## 2. Users

The Owner operating Drydock across repositories. The consumer is the Codex
pilot; the data may also be shown to the Owner.

## 3. Core Workflows

1. At a routing decision, request one sanitized usage snapshot.
2. Validate its schema, freshness, ranges, and attribution.
3. Combine valid remaining/reset evidence with separately measured burn.
4. Return `healthy`, `at_risk`, or `unavailable`.
5. Use the result to advise model/peer choice without changing tool authority
   or governance gates.

## 4. MVP Scope

- A local provider protocol over stdin/stdout or a bounded local file.
- A manual provider for Owner-entered capacity/reset values.
- An external-broker provider for a credential-owning tool that returns only
  sanitized JSON.
- Feature detection for a future official Claude structured usage command.
- Strict validation, short freshness, explicit source/attribution/limitations,
  and no raw-response persistence.
- Fake-provider deterministic tests.

The external broker is not bundled and is not trusted as enforcement evidence.
The current public macOS widget is research evidence, not the MVP dependency.

## 5. Non-Goals

- Credential discovery, token refresh, or direct Anthropic requests.
- Screen scraping the interactive `/usage` UI.
- Drydock-specific or model-specific attribution from account-wide data.
- Fable quota claims without evidence.
- Automatic permission, release, or governance decisions.
- Hosted telemetry or a Drydock usage database.

## 6. System Components

- `UsageProvider`: obtains one sanitized snapshot from an approved local
  source.
- `SnapshotValidator`: strict schema/range/time validation.
- `SanitizedCache`: stores only the validated snapshot and fetch time.
- `PaceForecaster`: consumes remaining/reset plus independently measured burn.
- `RoutingAdvisor`: recommends whether to spend a peer round; it owns no tools.

## 7. Data Model Sketch

```json
{
  "schema_version": 1,
  "source": "manual|external_broker|official_cli",
  "status": "current|stale|unavailable",
  "sampled_at": "ISO-8601 UTC",
  "freshness_seconds": 42,
  "attribution": "shared_account",
  "windows": [
    {
      "name": "five_hour|seven_day|provider_named",
      "utilization_percent": 61.5,
      "resets_at": "ISO-8601 UTC or null"
    }
  ],
  "limitations": ["account-wide; not Drydock-attributable"]
}
```

Unknown fields are rejected. Tokens, account identifiers, subscription
secrets, request headers, raw bodies, and prompts are forbidden.

## 8. Data Flow

Approved provider -> bounded local transport -> strict validator -> sanitized
short-lived cache -> pace forecast -> routing advice -> Owner-visible evidence.

Provider stderr is diagnostic only and must be scrubbed or omitted; it never
becomes usage evidence. Invalid or stale input terminates at `unavailable`.

## 9. API / Interface Boundaries

The provider is a separate local executable or manually supplied snapshot. It
receives no prompt, packet content, repository content, or Drydock credential.
It returns exactly one JSON document matching the snapshot contract.

A future official CLI provider may run only a documented, non-interactive,
structured usage command. The command is feature-detected; Drydock does not
infer support from version numbers or TUI text.

## 10. Auth & Permissions Assumptions

Drydock has no Claude credential permission. An external broker, if the Owner
installs one, owns its own authentication and is outside Drydock's trust
boundary. Its output is unsigned advisory input and can be forged by the local
user or compromised broker.

## 11. External Services / Integrations

The MVP has no required network service. A separate broker may talk to its own
provider, but Drydock neither knows nor receives its bearer token.

The observed private OAuth mechanism is deliberately not an integration:
`GET https://api.anthropic.com/api/oauth/usage` with the
`anthropic-beta: oauth-2025-04-20` header. The public widget reads Claude Code
credentials, can refresh and rewrite tokens, and maps `five_hour` and
`seven_day` usage windows. Those facts explain feasibility and risk; they do
not establish a supported Anthropic contract.

## 12. Risks & Tradeoffs

- Credential separation sacrifices turnkey automatic setup but preserves the
  current security boundary.
- Manual values are less convenient but are honest and immediately portable.
- An external broker can lie; therefore its signal stays advisory.
- Shared-account utilization includes other Claude clients and conversations.
- Two snapshots estimate account burn, not Drydock burn.
- Provider windows may appear, disappear, or change semantics.
- Cache improves resilience but requires visible freshness to avoid false
  confidence.

## 13. Implementation Phases

1. Owner and Claude approve the provider boundary and schema.
2. Implement strict snapshot types, validation, manual provider, and fixtures.
3. Implement bounded external-broker execution and sanitized cache.
4. Wire valid snapshots into `pace_forecast` and advisory routing.
5. Add an official CLI provider only when a documented command exists.
6. Consider a credential-owning helper only in a new explicit packet.

## 14. Testing Strategy

- Table tests for unknown fields, non-finite/out-of-range utilization, missing
  timestamps, future skew, stale samples, duplicate/unknown windows, and
  forbidden sensitive keys.
- Fake broker tests for timeout, non-zero exit, malformed/oversized JSON,
  stderr leakage, backoff, and last-good-but-stale reporting.
- Pace tests proving unavailable inputs never become healthy.
- Static tests forbidding token/header/raw-response fields in persisted data.
- No test calls Anthropic or reads a real credential store.

## 15. LaunchGuardian Handoff

Before a credential-owning helper or private endpoint ships, apply secrets and
config hygiene, third-party integration, dependency/supply-chain, privacy,
logging, failure-mode, and AI-agent security gates. The credential-free manual
provider has a smaller surface but still needs command execution, input
validation, and safe logging review.

## 16. Next Skill Recommendation

After Owner and peer approval: `backend` for the provider/validator/cache,
`mcp-ranger` for the privileged external broker boundary, and `testing` for
negative evidence cases. Run `launchguardian` before release if a
credential-bearing helper enters scope.

## Architecture Result

PASS WITH OPEN QUESTIONS. A useful credential-free MVP is defined.
Implementation remains BLOCKED until the Owner chooses the provider boundary
and Claude performs architectural peer review.
