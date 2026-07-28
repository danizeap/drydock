# Spec Delta: orchestration-efficiency-hardening

Capability: codex-host-orchestration

This delta changes orchestration efficiency mechanisms. It does not weaken
packet approval, peer-convergence truthfulness, independent verification,
LaunchGuardian, hook, integration, or release gates.

## ADDED Requirements

### Requirement: Every expensive phase has an explicit resource envelope
The controller SHALL bind each plan-peer, mutation, cross-review, verification,
and integration phase to a configured envelope containing elapsed-time,
model-call, outbound-input-byte, and provider-budget ceilings. It SHALL record
actual observed values and SHALL represent unavailable token or account usage
as unknown. Exhaustion SHALL produce a structured stop or reroute decision and
SHALL NOT create a PASS, convergence, or silent model downgrade.

#### Scenario: Usage data is unavailable
- **WHEN** the provider exposes no trustworthy token or remaining-capacity data
- **THEN** the phase reports usage unknown and still enforces the observable
  elapsed-time, call-count, input-byte, and configured-budget ceilings

#### Scenario: A phase reaches its envelope
- **WHEN** any configured ceiling is exhausted
- **THEN** no new automatic call starts and the result names the safe next
  route: smaller scope, an allowed right-sized model, or return to the Owner

### Requirement: Architecture peer critique precedes FULL mutation
For a FULL packet whose integration gate requires peer convergence, the
controller SHALL request architecture/security critique before starting a
mutating worker. If the peer is unavailable, work may follow the separately
specified single-pilot lifecycle rules, but peer convergence remains false and
integration SHALL remain gated wherever the packet requires it.

#### Scenario: Late review would force redesign
- **WHEN** a FULL plan changes persistence, permissions, process boundaries, or
  verification semantics
- **THEN** the peer sees the bounded plan and delta requirements before any
  mutating worker starts

### Requirement: A live equivalent invocation is never duplicated
The controller SHALL derive a request fingerprint from the candidate, bounded
request, model, schema, and relevant configuration. It SHALL persist bounded
invocation identity, process identity/lease, and terminal structured output.
While an equivalent invocation is live, another automatic invocation SHALL
attach to or report the existing call rather than start a duplicate. Stale
identity SHALL be rejected through process-identity and lease checks.

#### Scenario: Outer invoker is interrupted
- **WHEN** the shell or agent awaiting a peer call disappears while the bounded
  peer process remains live
- **THEN** a later controller observes the existing invocation and does not
  spend a second call

#### Scenario: Terminal output exists
- **WHEN** the peer reaches a schema-valid terminal result
- **THEN** the result is atomically durable before it is reported to the
  invoker and may be recovered by fingerprint

### Requirement: Oversized review input is refused before provider spend
The controller SHALL compare outbound bytes and the configured review-input
envelope before spawn. An oversized request SHALL NOT be truncated silently or
sent. The result SHALL disclose omitted scope and route to a repository-aware
Owner relay, separately approved snapshot mechanism, or smaller review whose
limitations remain explicit.

#### Scenario: Source bundle fits the legacy absolute cap but not the phase
budget
- **WHEN** a code-review payload is below the parser's absolute safety bound but
  above the configured review-input envelope
- **THEN** the controller refuses before provider spawn and reports
  `input_budget_exceeded`

### Requirement: Proof reuse is candidate- and command-bound
Reusable test or verification evidence SHALL bind the exact candidate
fingerprint, exact command, relevant environment fingerprint, terminal status,
and output digest. Evidence-only changes MAY reuse code proof. A source,
dependency, configuration, hook, generator, or unknown relationship SHALL
invalidate every affected proof. No cached result authorizes effects or
replaces an independent verifier.

#### Scenario: Evidence-only packet commit follows a frozen candidate
- **WHEN** only review/evidence Markdown or JSON changes after a full code pass
- **THEN** unaffected code-test evidence may be reused with the exact original
  candidate binding disclosed

#### Scenario: Changed relationship is unknown
- **WHEN** the controller cannot prove that a source or environment change is
  irrelevant to a prior command
- **THEN** that proof is invalidated and the command must run again

### Requirement: Test execution follows a targeted-to-full ladder
During mutation, the controller SHALL prefer the smallest checks that cover the
changed behavior. It SHALL freeze a candidate before the full required suite
and SHALL run that suite once per code fingerprint unless a failure or
subsequent invalidating change requires a bounded rerun. A corrected isolated
failure MAY be rechecked through its focused command while retaining the
already-passing command evidence when the invalidation rules prove it safe.

#### Scenario: Working-tree line endings break one bundle test
- **WHEN** the full adapter suite passes every behavior test but one
  deterministic bundle check fails from local CRLF bytes, and normalization
  changes no indexed content
- **THEN** the controller may rerun the affected bundle module plus parity
  check without repeating unrelated passing tests

## MODIFIED Requirements

### Requirement: Peer operational failures and control violations are distinct
Authentication, supported quota exhaustion, timeout, or ordinary process
failure MAY enter the explicit single-pilot workflow. A budget-ceiling
violation, malformed output, model mismatch, missing model/cost proof, or other
contract/control violation SHALL return to the Owner and SHALL NOT authorize
automatic continuation.

#### Scenario: Provider budget ceiling aborts the call
- **WHEN** the peer exits with `error_max_budget_usd`
- **THEN** the result is a budget control violation with
  `workflow.action: return_to_owner`, not `continue_codex_only`

### Requirement: Efficiency evidence uses observable facts
Dogfood records SHALL report actual elapsed time, call counts, input bytes,
commands, mode/model routing, and trustworthy provider/account evidence. They
SHALL NOT fabricate token counts or claimed savings. Automatic default
thresholds SHALL remain configurable and uncalibrated until supported by
multiple representative observations.

#### Scenario: Owner reports account-gauge consumption
- **WHEN** the Owner observes a weekly usage change that the controller cannot
  independently authenticate
- **THEN** the observation is labelled Owner-reported and is not converted into
  exact token consumption
