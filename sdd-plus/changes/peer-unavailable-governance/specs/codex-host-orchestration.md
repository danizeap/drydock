# Spec Delta: peer-unavailable-governance

Capability: codex-host-orchestration

This delta layers on the still-active `codex-host-mvp` capability delta. It
does not weaken that packet's peer, mutation, verification, or release gates.

## MODIFIED Requirements

### Requirement: Claude is an optional, bounded, structured peer
When authentication, quota, timeout, process, or service availability prevents
a usable peer round, the controller SHALL return a machine-readable
`single_pilot` decision that permits Codex-hosted lifecycle governance to
continue while stating that peer convergence was not established. A
contract-invalid result, including malformed output, model mismatch, unproven
model or cost, or a budget violation, SHALL return to the Owner rather than
authorize automatic continuation.

Before workflow start, the Owner MAY explicitly choose a Codex-only
`single_pilot` workflow. Its authority and plan SHALL omit the `peer` and
`cross_review` actions and the `plan_peer` and `cross_review` phases, and the
pilot SHALL NOT invoke peer authentication, status, or critique commands.
Every remaining packet, approval, isolated-mutation, proof, LaunchGuardian,
separate-verification, integration, and push gate still applies. Reports SHALL
state `peer_convergence: not_established` and SHALL NOT describe the result as
cross-model agreement or cross-model review.

#### Scenario: Owner selects Codex-only before provider spawn
- **WHEN** the Owner explicitly removes Claude from the current workflow before
  its authority and plan are created
- **THEN** the ordered workflow omits both peer phases, spends no Claude quota,
  preserves every non-peer gate, and reports single-pilot rather than
  two-brain convergence

#### Scenario: Claude is out of usage
- **WHEN** the peer returns an explicit supported rate-limit marker
- **THEN** the result reports `rate_limited`,
  `workflow.action: continue_codex_only`,
  `workflow.mode: single_pilot`, and
  `workflow.peer_convergence: not_established`

#### Scenario: Claude times out or its process fails
- **WHEN** a bounded peer call times out or returns an ordinary process failure
- **THEN** Codex may continue the governed packet without claiming peer
  agreement, cross-model review, or operational peer readiness

#### Scenario: Peer contract is invalid
- **WHEN** a response is malformed, names the wrong model, lacks required
  model/cost proof, or violates the configured budget
- **THEN** the workflow decision is `return_to_owner` and does not authorize
  automatic execution

#### Scenario: Failure text merely contains a keyword fragment
- **WHEN** unrelated error text contains `rate`, `quota`, or `usage` only as a
  substring or generic word, without an exact structured marker or explicit
  rate-limit phrase
- **THEN** the adapter SHALL NOT report `rate_limited`

## ADDED Requirements

### Requirement: Peer process cleanup is bounded
The peer adapter SHALL start Windows calls inside a kill-on-close Job Object
before their code runs, fail closed when that boundary cannot be established,
terminate the supported boundary on timeout, and bound the post-cleanup output
drain. It SHALL NOT resolve `taskkill` from `PATH`. POSIX process-group cleanup
SHALL be described as best effort rather than hostile descendant containment.

#### Scenario: Timed-out peer has a delayed descendant
- **WHEN** a peer process starts a descendant that would write a sentinel after
  the peer deadline
- **THEN** cleanup completes within the cleanup allowance, the direct peer is
  absent, and the delayed sentinel is not created

#### Scenario: Output pipes remain open after cleanup
- **WHEN** output cannot be drained within the bounded drain allowance
- **THEN** the adapter closes its pipe handles, returns a non-success cleanup
  result, and does not wait without a deadline
