# Build Blueprint: Adaptive Delegation Ledger

## 1. Product Goal

Give Drydock one durable, typed evidence substrate for every delegated model
call so later routing can balance capacity, cost, and demonstrated task
reliability without converting learned state into governance authority.

## 2. Users

The immediate consumer is the Codex-hosted Drydock controller. The Owner
benefits through more reliable and capacity-aware task allocation across Codex
and Claude.

## 3. Core Workflows

1. The controller creates one typed delegation envelope before a model call.
2. It records a bounded start event containing identifiers and digests, not
   model or repository content.
3. The adapter returns a normalized typed result and usage evidence.
4. A deterministic gate, peer, verifier, or Owner records a typed outcome
   observation.
5. The run-start capability profile remains frozen while shadow counts
   accumulate.
6. The controller may append the resulting capability profile commit only
   after recording terminal status `verified` and a safe verification evidence
   reference. The store validates that assertion's shape and state transition;
   the future live controller must establish the evidence's origin and result.
7. A future scheduler reads raw counts, aggregates, and confidence evidence to
   make an advisory routing recommendation.

## 4. MVP Scope

- Strict delegation, result, observation, and profile contracts.
- Append-only, bounded, hash-linked run events.
- Frozen profile snapshots and pure shadow reduction.
- Append-only optimistic profile commit after a controller-recorded verified
  terminal assertion.
- Cross-platform, stdlib-only implementation and deterministic tests.

## 5. Non-Goals

- Claude credentials, usage collection, or provider calls.
- Automatic routing or a reliability scalar.
- Emotional/personality relationship state.
- A dashboard.
- Runtime integration with every existing Drydock adapter.
- Authentication, hostile-user tamper resistance, or an externally anchored
  transparency log.

## 6. System Components

- `delegation_contracts.py`: strict immutable value contracts, normalization,
  canonical JSON, digests, bounds, and sensitive-field rejection.
- `delegation_ledger.py`: serialized append, chain verification, and honest
  integrity report.
- `capability_profiles.py`: raw evidence aggregates, frozen snapshots, pure
  shadow reducer, immutable source samples, exact commit-time recomputation,
  and controller-asserted verified-terminal commit log.
- Focused adapter tests using only temporary directories and fake data.

## 7. Data Model Sketch

`DelegationEnvelope`:

- run/delegation/task identifiers;
- task class and role;
- provider, model, reasoning effort, and requested permission profile;
- deterministic idempotency key;
- attempt bounds;
- objective and input digests;
- optional capacity-snapshot digest;
- policy revision and creation time.

`DelegationResult`:

- delegation ID and normalized terminal status;
- duration;
- normalized token counts with missing values preserved as `null`;
- bounded artifact/evidence references;
- bounded error code and summary.

`OutcomeObservation`:

- unique observation and delegation IDs;
- observer kind;
- acceptance/revision/rejection/unavailable state;
- independent verification state;
- findings/regression counts;
- evidence references and timestamp.

`CapabilityProfile` key:

`provider | model | role | task_class`

The profile stores raw sample, completion, timeout, invalid-output,
verification-pass/fail, revision, rejection, finding, regression, token, and
duration counts. It does not store authority or a final routing score.

## 8. Data Flow

Runtime objective and repository inputs remain in the existing bounded adapter
path. The ledger receives only their SHA-256 digests and safe metadata.

Envelope -> start event -> normalized result -> outcome observation -> shadow
reducer -> frozen comparison -> verified terminal commit -> future scheduler.

## 9. API / Interface Boundaries

The modules expose local Python functions and dataclasses only. Unknown fields
enter only through strict `from_dict` methods and are rejected. Persistent
records are canonical JSONL. No network listener or external API is added.

## 10. Auth & Permissions Assumptions

The files are local, unsigned, and user-writable. Hash linking detects mutation,
reordering, or sequence gaps within the observed file; it does not authenticate
the writer or prove that a suffix was not deleted. The controller remains the
single logical writer, while an OS file lock serializes physical appends.

Capability evidence has no authority to change permission profiles, tool
access, governance gates, convergence, reviewer independence, or Owner
approval.

## 11. External Services / Integrations

None in this packet. Codex and Claude adapters become consumers in later
packets. All tests are local and spend no quota.

## 12. Risks & Tradeoffs

- Strict schemas create adapter work but prevent silent evidence drift.
- Full profile snapshots in commits cost more disk than mutable state but make
  rollback and audit simple.
- Raw counts avoid false precision but defer scheduler policy.
- Known-pattern secret rejection and forbidden raw-content field aliases reduce
  accidental persistence but cannot prove arbitrary safe-looking text is
  content-free. Future adapters must persist only typed contract projections;
  the substrate does not claim semantic data-loss prevention.
- Aggregate snapshots are recomputed from their immutable in-memory source
  contracts at commit; arbitrary same-process code could still fabricate those
  source observations, so this is correctness checking rather than
  authenticated attestation.
- A local unkeyed chain is corruption evidence, not adversarial attestation.
- A `verified` string and safe evidence reference are state-machine inputs, not
  proof that a verifier ran, passed, or was independent. That binding belongs
  to the later live-controller integration packet.

## 13. Implementation Phases

1. Contracts and validators.
2. Run ledger and verification.
3. Capability profiles, shadow reducer, and verified commit log.
4. Focused/adversarial tests.
5. Independent Codex verification.
6. Claude peer review when available.
7. Later integration with automatic capacity-aware routing.

## 14. Testing Strategy

- Unit tests for every enum, bound, digest, ID, usage, reference, unknown-field,
  non-finite, and sensitive-field rule.
- Storage tests for append, concurrent sequence allocation, mutation,
  reordering, truncation disclosure, malformed JSON, and oversized lines.
- Profile tests for frozen-state preservation, raw aggregate math, duplicate
  observation refusal, current-state conflicts, and unverified commit refusal.
- No mock test may assert only its own fixture; tests inspect persisted bytes
  and reconstruct state through public readers.

## 15. LaunchGuardian Handoff

This is not a release packet. Before the ledger affects live routing, evaluate
agent security, secrets/logging, resilience, privacy/data lifecycle, and
observability gates. A future Claude credential broker remains a separate,
explicitly approved high-risk boundary.

## 16. Next Skill Recommendation

Use `backend` to integrate these contracts into adapters and the automatic
capacity scheduler after this substrate passes independent review. Use
`mcp-ranger` only when implementing the Claude credential-owning broker.

## Architecture Result

PASS WITH OPEN QUESTIONS. The local credential-free substrate is ready to
implement. Claude peer review and routing calibration remain explicit pending
gates and cannot be replaced by the implementer's report.
