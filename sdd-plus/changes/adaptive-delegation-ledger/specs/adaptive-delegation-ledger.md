# Spec Delta: adaptive-delegation-ledger

Capability: adaptive-delegation-ledger

## ADDED Requirements

### Requirement: Delegation evidence uses strict content-minimal contracts

Drydock SHALL represent each delegated call, normalized result, and outcome
observation with a strict versioned contract. Unknown fields, duplicate JSON
keys, non-finite numbers, invalid identifiers, unsafe references, inconsistent
usage totals, and configured size/depth/cardinality overflow SHALL be rejected.
Persistent contracts SHALL contain objective and input digests rather than raw
prompts, repository content, provider bodies, credentials, authorization
headers, account identifiers, or file contents.

#### Scenario: Otherwise valid record carries a prompt

- **WHEN** a contract includes an otherwise valid payload plus a raw `prompt`
  field
- **THEN** the entire contract is rejected before any bytes are persisted

#### Scenario: Partial usage is not invented

- **WHEN** a provider supplies input tokens but no output tokens
- **THEN** normalized total tokens remains unavailable rather than equaling the
  known input count

### Requirement: Run events are append-only and locally self-verifying

Drydock SHALL serialize event appends across supported operating systems,
verify the existing event stream before appending, allocate contiguous
sequences under the same lock, write canonical JSONL, flush and fsync before
reporting success, and link every record to the preceding record digest.

#### Scenario: Two writers append concurrently

- **WHEN** two supported processes append to the same run ledger
- **THEN** the resulting stream contains two intact records with distinct
  contiguous sequences and a valid digest chain

#### Scenario: Existing record was modified

- **WHEN** an existing record's status or payload is changed before a new
  append
- **THEN** verification fails and the append is refused

### Requirement: Integrity reports do not claim authentication

Every successful ledger verification SHALL state that records are unkeyed and
user-writable, that writer authenticity is not established, and that deletion
of an unanchored suffix is not ruled out. Absence of detected corruption SHALL
NOT be reported as proof of authenticity or completeness.

#### Scenario: Observed chain is internally valid

- **WHEN** every observed line, sequence, and digest verifies
- **THEN** the result may report internal chain validity but still reports
  authenticity and suffix-completeness as unavailable

### Requirement: Capability learning is task-specific and non-authoritative

Capability profiles SHALL be keyed by provider, model, role, and task class and
SHALL store observable counts and cost aggregates rather than an interpersonal
trust label or one authority-bearing score. Profile evidence SHALL NOT
authorize effects, change permissions, waive governance, select verifier
independence, establish peer convergence, or override the Owner.

#### Scenario: One executor has the strongest history

- **WHEN** one profile has more verified successes than every alternative
- **THEN** that evidence may later inform routing but grants no permission and
  waives no required review or verification

### Requirement: Learning remains frozen during a run

Drydock SHALL apply unique outcome observations to a deep shadow copy of the
run-start capability snapshot. Caller-owned collections SHALL be detached into
immutable tuples. The shadow SHALL retain the source envelope, result, and
observation contracts, and the profile store SHALL recompute the exact
aggregate snapshot from those sources before commit. The run-start snapshot
and policy SHALL remain unchanged throughout the run.

#### Scenario: Shadow outcome is applied

- **WHEN** a completed delegation outcome is reduced into the shadow profile
- **THEN** the shadow counts change while the frozen start digest and content
  remain byte-for-byte unchanged

#### Scenario: Observation is replayed

- **WHEN** a shadow batch repeats an observation ID
- **THEN** the batch is rejected rather than double-counted

#### Scenario: Caller fabricates monotonic aggregate totals

- **WHEN** a shadow has one source observation but its snapshot carries
  different finding, usage, duration, or outcome aggregates
- **THEN** commit-time exact recomputation rejects the shadow

### Requirement: Persistent learning requires a verified terminal assertion

Drydock SHALL append a capability-profile commit only when the current
persistent state still equals the frozen run-start digest, the shadow snapshot
is valid, all observation IDs are new, terminal status is exactly `verified`,
and a safe relative verification-evidence reference is present. This local
store SHALL treat terminal status and the reference as controller assertions;
it SHALL NOT claim that their shape proves the artifact exists, the verdict
passed, or the verifier was an independent process. Live integration SHALL
establish those properties before it invokes the commit.

#### Scenario: Run implemented but not independently verified

- **WHEN** a run is complete but terminal status is not `verified`
- **THEN** no capability profile commit is appended

#### Scenario: Another run advanced learning

- **WHEN** persistent profile state no longer matches the run-start digest
- **THEN** the commit fails with a conflict and does not overwrite or merge the
  newer state

#### Scenario: Verified run commits

- **WHEN** all commit preconditions hold
- **THEN** one append-only profile commit records the new snapshot, observation
  IDs, verification reference, prior state digest, and new state digest

#### Scenario: Evidence reference has valid syntax only

- **WHEN** the store receives `verified` and a safe relative reference without
  live-controller provenance evidence
- **THEN** the store may validate the state transition but does not report that
  independent verification was established
