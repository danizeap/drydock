# Spec Delta: orchestration-efficiency-hardening

Capability: codex-host-orchestration

This delta changes orchestration efficiency mechanisms. It does not weaken
packet approval, peer-convergence truthfulness, independent verification,
LaunchGuardian, hook, integration, or release gates.

## ADDED Requirements

### Requirement: Every expensive phase and the whole run have explicit resource envelopes
The controller SHALL bind each plan-peer, mutation, cross-review, verification,
and integration phase to a configured envelope containing elapsed-time,
model-call, outbound-input-byte, and provider-budget ceilings. The controller
SHALL also enforce cumulative ceilings over the entire run so phase limits
cannot multiply beyond the Owner's run boundary. It SHALL record actual
observed values and SHALL represent unavailable token or account usage as
unknown. Exhaustion SHALL produce a structured stop or advisory-reroute
decision and SHALL NOT create a PASS or convergence.

#### Scenario: Usage data is unavailable
- **WHEN** the provider exposes no trustworthy token or remaining-capacity data
- **THEN** the phase reports usage unknown and still enforces the observable
  elapsed-time, call-count, input-byte, and configured-budget ceilings

#### Scenario: A phase reaches its envelope
- **WHEN** any configured ceiling is exhausted
- **THEN** no new automatic call starts and the result names the safe next
  route: smaller scope, an advisory-only right-sized model, or return to the
  Owner

#### Scenario: The cumulative run envelope is exhausted
- **WHEN** aggregate elapsed time, call count, outbound bytes, or configured
  provider spend reaches the run ceiling even though the current phase has room
- **THEN** the run stops before another automatic call and returns the
  remaining work to the Owner

#### Scenario: A cheaper model is available after exhaustion
- **WHEN** an exhausted phase routes a bounded task to a cheaper or otherwise
  different model
- **THEN** its output is advisory only and SHALL NOT satisfy peer convergence,
  architecture critique, cross-review, or independent verification for the
  exhausted phase

### Requirement: Objective high-impact properties trigger pre-mutation peer critique
For every FULL change that affects persistence, permissions, process
boundaries, or verification semantics, the controller SHALL request
architecture/security critique before starting a mutating worker. This trigger
depends on the affected behavior, not on packet-authored gate labels. If
critique is unavailable and existing single-pilot rules permit lifecycle work,
the controller SHALL emit a machine-readable `critique_skipped` disclosure with
reason and `peer_convergence: not_established`; the missing critique SHALL NOT
satisfy an integration or review gate.

#### Scenario: Late review would force redesign
- **WHEN** a FULL plan changes persistence, permissions, process boundaries, or
  verification semantics
- **THEN** the peer sees the bounded plan and delta requirements before any
  mutating worker starts

#### Scenario: Packet omits a peer gate
- **WHEN** objective high-impact properties apply but the packet does not name
  peer convergence as an integration gate
- **THEN** pre-mutation critique is still required

#### Scenario: Critique cannot be obtained
- **WHEN** a supported operational failure prevents the pre-mutation critique
- **THEN** the result records `critique_skipped`, the exact operational reason,
  and `peer_convergence: not_established`

### Requirement: A live equivalent invocation is never duplicated
The controller SHALL derive a request fingerprint from the candidate, bounded
request, model, schema, and relevant configuration. It SHALL persist bounded
invocation identity, process identity/lease, and eligible terminal structured
output. While an equivalent invocation is live, another automatic invocation
SHALL attach to or report the existing call rather than start a duplicate.
Stale identity SHALL be rejected through process-identity and lease checks. An
expired lease without a terminal result SHALL return to the Owner and SHALL
NOT authorize an automatic restart.

#### Scenario: Outer invoker is interrupted
- **WHEN** the shell or agent awaiting a peer call disappears while the bounded
  peer process remains live
- **THEN** a later controller observes the existing invocation and does not
  spend a second call

#### Scenario: Terminal output exists
- **WHEN** the peer reaches a schema-valid terminal result
- **THEN** the result is atomically durable before it is reported to the
  invoker and may be recovered by fingerprint within its freshness bound

#### Scenario: Lease expires without terminal output
- **WHEN** the recorded process identity is absent or mismatched, the lease is
  expired, and no terminal result was durably recorded
- **THEN** the controller reports an indeterminate interrupted call and returns
  to the Owner without automatically spending a replacement call

### Requirement: Durable peer results are bounded, screened, fresh, and out of tree
Invocation state SHALL live in an application-owned local state directory
outside the repository and known synchronized trees. It SHALL never persist
the outbound prompt or source bodies. Before a terminal result body is stored,
a dedicated at-rest content secret screen SHALL pass and the canonical body
SHALL be at most 64 KiB. An ineligible body SHALL leave only its digest,
terminal classification, and non-sensitive reason. Recoverable bodies SHALL
carry original observation time, exact fingerprint, and SHALL expire no later
than 24 hours after observation. The stored body SHALL be deleted by that
deadline; expired bounded metadata SHALL NOT satisfy a current gate. The store
is user-writable and SHALL NOT be described as authenticated or as attestation.

#### Scenario: Peer result contains secret-shaped content
- **WHEN** the terminal structured result matches the at-rest secret screen
- **THEN** the body is not persisted and recovery reports
  `terminal_result_not_persisted` with bounded digest/status metadata

#### Scenario: Recovered result is stale
- **WHEN** a matching terminal result is older than 24 hours
- **THEN** it is reported with its original observation time but SHALL NOT
  satisfy critique, convergence, review, or verification

#### Scenario: Worktree is inspected
- **WHEN** durable orchestration state is written or cleaned
- **THEN** no state file exists under the repository or changes its Git
  candidate fingerprint

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
and output digest. Reuse SHALL require a clean committed Git tree with no
untracked files; the candidate fingerprint SHALL bind the complete tracked tree
rather than only its diff. A source, dependency, configuration, hook, generator,
loadable file, environment, or unknown relationship SHALL invalidate every
affected proof. No cached result authorizes effects or replaces an independent
verifier. Reuse is an intermediate-work optimization only.

#### Scenario: Working tree is dirty or contains untracked files
- **WHEN** Git reports any tracked modification or untracked path, including a
  loadable `conftest.py`, `sitecustomize.py`, `.pth`, or bytecode artifact
- **THEN** proof reuse is disabled and no prior result is attached to the
  current candidate

#### Scenario: Changed relationship is unknown
- **WHEN** the controller cannot prove that a source or environment change is
  irrelevant to a prior command
- **THEN** that proof is invalidated and the command must run again

### Requirement: Test execution follows a targeted-to-full ladder
During mutation, the controller SHALL prefer the smallest checks that cover the
changed behavior. It SHALL freeze a candidate before the full required suite
and SHALL run the complete required suite against the exact final candidate
fingerprint. Targeted checks and composed or reused proof MAY accelerate
intermediate fingerprints only. Any tracked change after the full run creates
a new candidate that SHALL receive its own complete required-suite execution
before final acceptance.

#### Scenario: Isolated intermediate failure is corrected
- **WHEN** a focused correction produces a new intermediate fingerprint
- **THEN** the affected focused command may run immediately, but that composed
  evidence SHALL NOT replace the full required suite on the final fingerprint

#### Scenario: Evidence file changes after the final suite
- **WHEN** any tracked packet, evidence, source, or configuration byte changes
  after the complete suite ran
- **THEN** the candidate fingerprint changes and final acceptance remains
  unsatisfied until the complete required suite runs on the new fingerprint

## MODIFIED Requirements

### Requirement: Peer operational failures and control violations are distinct
Only an explicitly enumerated allowlist of benign availability failures MAY
enter the single-pilot workflow: authentication unavailable before spawn, an
exact supported rate-limit marker, a controller timeout with bounded cleanup,
or an ordinary non-zero process exit that carries no structured provider
subtype. A budget ceiling, policy/refusal/context-limit abort, malformed output,
model mismatch, missing model/cost proof, unknown structured subtype, unmapped
stage, or other contract/control violation SHALL return to the Owner and SHALL
NOT authorize automatic continuation. The default for every unrecognized value
is `return_to_owner`.

#### Scenario: Provider budget ceiling aborts the call
- **WHEN** the peer exits with `error_max_budget_usd`
- **THEN** the result is a budget control violation with
  `workflow.action: return_to_owner`, not `continue_codex_only`

#### Scenario: Provider adds an unknown subtype
- **WHEN** a peer failure carries a structured subtype that appears nowhere in
  the controller's allowlist
- **THEN** the result is `unmapped_control_failure` with
  `workflow.action: return_to_owner`

#### Scenario: Ordinary process exits without a provider subtype
- **WHEN** the bounded peer exits nonzero, cleanup is complete, and no
  structured provider subtype or contract output exists
- **THEN** the explicit ordinary-process-exit allowlist entry may enter
  single-pilot with convergence not established

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

### Requirement: Observable efficiency surfaces are not overclaimed
The controller SHALL enforce and report the subprocess calls, request bytes,
elapsed time, configured budgets, and provider/account signals it can directly
observe. It SHALL NOT claim to measure all provider-side reasoning tokens,
context-cache behavior, or nested-worker context ingestion when those surfaces
are unavailable. The orchestrated workflow SHALL allow no more than one active
mutator per worktree, one equivalent peer/reviewer call per request
fingerprint, and one verifier per final candidate unless the Owner explicitly
authorizes a replacement after a terminal failure.

#### Scenario: Worker loads broad internal context
- **WHEN** the provider does not expose nested-worker context ingestion
- **THEN** Drydock reports that cost surface as unobserved rather than claiming
  the phase envelope measured it

#### Scenario: Equivalent reviewer already exists
- **WHEN** a matching reviewer invocation is active or a fresh eligible
  terminal result exists
- **THEN** the controller attaches or recovers it and does not start another
  automatic reviewer
