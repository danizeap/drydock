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
   with `controller_asserted_status="passed"` and a safe
   `asserted_verification_ref`. These are unauthenticated controller
   assertions. The store validates only their shape and the state transition;
   the future live controller must establish evidence existence/origin, an
   actual pass result, and verifier independence.
7. A future scheduler reads raw counts, aggregates, and confidence evidence to
   make an advisory routing recommendation.

## 4. MVP Scope

- Strict delegation, result, observation, and profile contracts.
- Append-only, bounded, hash-linked run events.
- Frozen profile snapshots and pure shadow reduction.
- Append-only optimistic profile commit after an unauthenticated
  controller-recorded `passed` assertion.
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
- `delegation_ledger.py`: serialized append, chain verification, honest
  integrity reporting, and an atomic repair candidate containing a canonical
  reserved in-chain marker.
- `capability_profiles.py`: raw evidence aggregates, frozen snapshots, pure
  shadow reducer, immutable source samples, exact commit-time recomputation,
  and unauthenticated controller-asserted `passed` commit log.
- Focused adapter tests using only temporary directories and fake data.

## 7. Data Model Sketch

`DelegationEnvelope`:

- run/delegation/task identifiers;
- task class and role;
- provider, model, reasoning effort, and requested permission profile;
- canonical request-binding digest (not an idempotency claim);
- attempt bounds;
- objective and input digests;
- optional capacity-snapshot digest;
- policy revision and creation time.

`DelegationResult`:

- delegation ID and normalized terminal status;
- controller-observed runtime status, separate from optional untrusted claimed
  terminal status and untrusted nested error detail;
- duration;
- normalized token counts with missing values preserved as `null`;
- bounded artifact/evidence references;
- bounded error code and summary.

`OutcomeObservation`:

- unique observation and delegation IDs plus run ID and the canonical full
  envelope/result digests;
- observer kind;
- acceptance/revision/rejection/unavailable state;
- independent verification state;
- findings/regression counts;
- evidence references and timestamp.

`CapabilityProfile` key:

`provider | model | role | task_class`

The profile stores raw sample, completion, timeout, invalid-output,
verification-pass/fail, revision, rejection, finding, regression, token, and
duration counts. Duplicate and binding/content conflicts are typed durable
rejection counters. It does not store authority or a final routing score.

## 8. Data Flow

Runtime objective and repository inputs remain in the existing bounded adapter
path. The ledger receives only their SHA-256 digests and safe metadata.

Envelope -> start event -> normalized result -> outcome observation -> shadow
reducer -> frozen comparison -> controller-asserted `passed` commit -> future
scheduler.

## 9. API / Interface Boundaries

The modules expose local Python functions and dataclasses only. Unknown fields
enter only through strict `from_dict` methods and are rejected. Persistent
records are exact canonical JSONL: sorted-key, ASCII-escaped, compact
serialization followed by one LF byte. Semantically equivalent whitespace,
CRLF, key order, or escaping is corruption. No network listener or external
API is added.

The exact serializer is Python `json.dumps` with `sort_keys=True`,
`separators=(",", ":")`, `ensure_ascii=True`, and `allow_nan=False`.
Serialization preserves the exact Python code-point sequence without Unicode
normalization; equivalent Unicode spellings remain different bytes and
digests. Binary I/O emits exactly one LF. Numeric scope is finite Python JSON
integers/floats under the schema bounds. This is not a cross-language
canonicalization claim.

Profile commits retain every full source triple and deterministic typed
decision so replay starts empty and reconstructs indexes, aggregates,
snapshots, and final bytes. The hard profile limits are 32 commits and 64
source submissions per commit.

## 10. Auth & Permissions Assumptions

The files are local, unsigned, and user-writable. Hash linking detects mutation,
reordering, or sequence gaps within the observed file; it does not authenticate
the writer or prove that a suffix was not deleted. The controller remains the
single logical writer, while an OS file lock serializes physical appends.

That lock is a sidecar file initialized with one NUL at byte zero, using binary
`a+b` writer handles and existing-file `r+b` read handles without writes. Each
attempt `seek(0)`. Windows applies custom nonblocking `msvcrt.LK_NBLCK` to the
one-byte range at byte zero; POSIX applies
`fcntl.flock(..., LOCK_EX | LOCK_NB)` to the sidecar file, independent of the
seek offset. Attempts retry every 25 ms against a monotonic caller-selected
timeout capped at 30 seconds. Initialization is performed after the selected
lock is acquired under racing opens. Closing the OS handle, including process
crash, releases the lock; there is no stale PID-file policy. Only the tested
serialization/release behavior is shared; semantic identity between the OS
primitives is not claimed.

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
- Torn-tail repair accepts only a bounded strict structural prefix. Every
  existing immutable intent must match reachable locked bytes: the exact
  before-state classification or the exact prefix-plus-marker candidate/current
  stream.
  The candidate is the exact valid prefix plus a canonical reserved
  `drydock_repair` event. Its marker fields, length, digest, record count, final
  digest, and any later stream are recomputed, and a selected
  before-digest-derived quarantine is required for completed replay.
- `controller_asserted_status="passed"` and
  `asserted_verification_ref` are unauthenticated state-machine inputs, not
  proof that evidence exists, has a particular origin, records a pass, or came
  from an independent process. They grant no permission or authority.
- Accepted run-ledger ceilings are 10,000 records, 16 MiB total, and 32 KiB
  per line. Profile history ceilings are 32 commits and 64 submissions per
  commit. Capacity overflow is a hard refusal, not truncation or throughput
  evidence.
- Default timestamps use the OS UTC wall clock to millisecond precision;
  accepted caller timestamps use the same exact grammar but are not required
  to be monotonic. File fsync applies on all supported OSes; parent-directory
  fsync applies on POSIX only, so Windows power-loss durability is weaker even
  though atomic replacement and crash replay remain tested behavior.

## 13. Implementation Phases

1. Contracts and validators.
2. Run ledger and verification.
3. Capability profiles, shadow reducer, and controller-asserted commit log.
4. Focused/adversarial tests.
5. Independent Codex verification.
6. Claude peer review when available.
7. Later integration with automatic capacity-aware routing.

## 14. Testing Strategy

- Unit tests for every enum, bound, digest, ID, usage, reference, unknown-field,
  non-finite, and sensitive-field rule.
- Storage tests for append, concurrent sequence allocation, mutation,
  reordering, every noncanonical byte representation, truncation disclosure,
  malformed JSON, relational intent/candidate/quarantine replay, and oversized
  lines.
- Profile tests for frozen-state preservation, raw aggregate math, duplicate
  and conflict decision persistence, source/decision tamper, 32-commit and
  64-submission ceilings, current-state conflicts, non-`passed` refusal, and
  fabricated controller assertion acceptance without authentication.
- No mock test may assert only its own fixture; tests inspect persisted bytes
  and reconstruct state through public readers.

Fresh-checkout verification also rebuilds
`project-scaffold.bundle.json` from Git-normalized LF source and refuses CRLF
in text entries. The stale generated bundle predates this ledger remediation
and is documented as a verification prerequisite, not a ledger-caused defect.
The global `.gitattributes` rule `* text=auto eol=lf` already covers it; no
duplicate path rule is needed. Because the bundle is consumed by the plugin,
rollback rebuilds the bundle from deliberately reverted scaffold source rather
than deleting the artifact.

Existing `.github/workflows/ci.yml` already runs `tests/` and
`adapters/codex/tests/` on Ubuntu and Windows with Python 3.9 and 3.12.
Local commands/results are recorded separately in `verification.md`; no
redundant CI workflow belongs in this packet.

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

PASS WITH OPEN QUESTIONS. The local credential-free substrate is implemented
for this packet and awaits independent verification. Claude peer review and
routing calibration remain explicit pending gates and cannot be replaced by
the implementer's report.
