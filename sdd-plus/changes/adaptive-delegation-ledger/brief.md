# Brief

## Change

adaptive-delegation-ledger

## Intake

Mode: FULL framework architecture and implementation. Primary skill:
`architect`. Supporting skill: `testing`, because the new persistence and
learning boundaries require adversarial contract, corruption, replay, and
commit-gate proof.

The 2026-07-28 schema-v2 remediation is a bounded FULL backend repair.
`backend` is primary and `testing` supports the corruption, recovery, and
capacity proof. It does not authorize archive, release, or self-verification.

## User Need

Let Drydock learn which provider/model combinations are reliable and efficient
for particular task classes without converting a vague interpersonal "trust"
score into governance authority. The same evidence must later support automatic
capacity-aware delegation and survive task, process, and chat handoffs.

## Problem

Drydock has several structured subprocess results and per-call usage fields,
but no shared delegation contract or durable run ledger across Codex, Claude,
and future executors. Task cost, verification outcomes, retry behavior, and
review yield therefore cannot be reduced into a provider/model/task-class
history without reconstructing incompatible logs.

The ZeroHandoff reference demonstrates useful mechanics: typed invocation
boundaries, immutable artifact attempts, append-only events, frozen run-start
learning state, shadow updates, and a bounded end-of-run commit. Its learned
variable is not suitable as-is for Drydock: binary handoff acceptance is too
noisy to represent interpersonal trust, same-model personas do not establish
epistemic diversity, and learned state must never authorize effects or waive
governance.

## Scope

In scope:

- A strict, stdlib-only `DelegationEnvelope` and `DelegationResult` contract.
- A local append-only, hash-linked run ledger with bounded sanitized payloads.
- Honest ledger verification that names its lack of authentication and
  suffix-truncation protection.
- Task-specific capability profiles made only of observable counts and cost
  aggregates, not one authority-bearing trust score.
- Frozen profile snapshots, duplicate-resistant shadow reduction, and a
  verified-terminal-only append commit.
- Deterministic Windows/macOS/Linux tests with no provider calls or quota use.
- Strict schema-v2 request binding, controller-observed runtime status, and
  explicitly untrusted claimed terminal/error detail.
- Durable full source submissions with typed accepted, duplicate, and conflict
  decisions that replay into the exact same profile state.
- Exact canonical JSON bytes plus LF for every accepted ledger/profile line.
- Explicit relational torn-tail repair whose immutable intent, candidate,
  optional quarantine, and later reachable ledger bytes must agree.

Out of scope:

- Claude credential access or usage telemetry.
- Automatic provider/model allocation.
- A Control Room UI.
- Retrofitting every existing conductor path in this packet.
- Emotional/personality relationship dimensions.
- A scalar score that can authorize tools, waive gates, select the verifier,
  prove convergence, or override the Owner.
- Copying ZeroHandoff runtime code.

## Acceptance Criteria

- [ ] Unknown, duplicate, non-finite, oversized, or secret-shaped contract
  data fails closed before persistence.
- [ ] The persisted delegation envelope contains objective/input digests but
  no raw prompt, repository content, provider response, or credential.
- [ ] Run-event appends are serialized across supported operating systems and
  verify their sequence and hash chain.
- [ ] Ledger verification reports corruption positively but reports
  authenticity and suffix-truncation protection as unavailable.
- [ ] Capability profiles are keyed by provider, model, role, and task class
  and retain raw observed counts plus usage/duration aggregates.
- [ ] Applying outcomes produces a shadow snapshot without mutating the
  run-start snapshot.
- [ ] A profile commit recomputes the exact shadow snapshot from immutable
  source contracts rather than trusting caller-supplied aggregates.
- [ ] A profile commit is refused unless the current state still equals the
  frozen start, observations are unique, and the controller records terminal
  status `verified` plus a safe evidence reference.
- [ ] The store explicitly does not claim that this reference proves the
  artifact exists, passed, or came from an independent process; live
  integration must establish those properties.
- [ ] No learned evidence changes permissions, gates, convergence, or Owner
  authority.
- [ ] Focused tests pass on this machine; complete verification and a separate
  reviewer remain required before archive or release.
- [ ] Claude later reviews the contracts, adversarial boundaries, and
  calibration plan when usage returns.
- [ ] Profile history enforces exactly 32 commits, at most 64 submitted source
  triples per commit, and typed persisted rejections for duplicate/conflicting
  evidence.
- [ ] Whitespace, CRLF, key-order, or escaping mutations make a ledger/profile
  stream corrupt and block append/commit.
- [ ] Torn-tail classification is bounded and never leaks raw parser recursion
  or integer-conversion exceptions; existing repair metadata is relationally
  checked before replay.
- [ ] The generated scaffold bundle is rebuilt from LF source and rejects CRLF
  in text entries. This is a fresh-checkout verification prerequisite caused
  by the pre-existing committed bundle, not by delegation-ledger behavior.

## Impact Areas

- Backend: new Codex-host orchestration substrate.
- Frontend: none.
- Data model: delegation, result, event, observation, profile, and profile
  commit contracts.
- API: local Python interfaces only; no network API.
- AI/model behavior: future routing input only; no automatic routing here.
- Documentation: new delta spec and Build Blueprint.
- Operations/security: local logs must exclude model content and credentials;
  files remain unsigned and user-writable.

## Open Questions

- Which conservative routing algorithm should consume capability profiles
  after enough dogfood samples exist?
- What minimum sample count should permit a learned estimate to influence the
  automatic capacity scheduler?
- Claude peer review is pending for the exact schema, attack surface, and
  calibration policy.
