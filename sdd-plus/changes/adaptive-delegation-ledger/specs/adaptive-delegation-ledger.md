# Spec Delta: adaptive-delegation-ledger

Capability: adaptive-delegation-ledger

## ADDED Requirements

### Requirement: Persisted delegation evidence uses strict schema v2

Drydock SHALL persist only schema version 2 delegation envelopes, results,
observations, run events, capability snapshots, source submissions, reduction
decisions, profile commits, and repair intents. Every schema-v1 value SHALL be
refused; this change has no automatic or silent v1 migration path.

Strict JSON input SHALL reject duplicate object keys; `NaN`, `Infinity`, and
`-Infinity`; finite-number overflow such as `1e400`; integers with more than 19
decimal digits or magnitude above the configured signed-63-bit bound; and a
value deeper than eight parent-to-child edges with the root at depth zero.
Parser recursion failure SHALL be reported as the same typed contract error as
other invalid JSON.

Timestamps SHALL match `YYYY-MM-DDTHH:MM:SS.mmmZ` exactly and SHALL also be a
real UTC calendar time. Generic payload objects and untrusted nested error
claims SHALL be validated and recursively copied before a contract or event
retains them.

The envelope SHALL persist a canonical request-binding digest, not an
idempotency claim. The result SHALL keep controller-observed runtime status
separate from optional untrusted in-band claimed terminal status and untrusted
error detail. Token usage SHALL declare reported, estimated, or unavailable
basis plus whether reported reasoning tokens are included in or excluded from
output tokens. Cost SHALL independently declare reported, estimated, or
unavailable basis.

The generic event payload boundary is exact JSON-compatible metadata subject
to the byte, depth, item-count, string, numeric, duplicate-key, and
known-secret-shape validators. It is not a semantic guarantee that arbitrary
safe-looking strings are minimal or secret-free.

#### Scenario: Schema v1 is presented

- **WHEN** any persisted v1 contract, event, profile commit, or repair intent is
  read
- **THEN** the read is corrupt/unsupported and no v2 state is appended

#### Scenario: JSON nesting reaches the boundary

- **WHEN** strict JSON has descendant depth eight
- **THEN** it is accepted if every other value satisfies the boundary
- **AND WHEN** descendant depth is nine
- **THEN** it is rejected with a typed contract error

#### Scenario: Python would otherwise accept a special number

- **WHEN** JSON contains `NaN`, `Infinity`, `-Infinity`, `1e400`, or an integer
  outside the deterministic digit/magnitude bound
- **THEN** the JSON is rejected before contract construction or persistence

#### Scenario: Caller mutates nested input after construction

- **WHEN** the caller changes a nested source payload or untrusted error object
  after constructing the event or result
- **THEN** the canonical bytes subsequently persisted from the constructed
  value remain unchanged

### Requirement: Run events are fully verified append-only observations

Drydock SHALL operate each run ledger as a single-logical-writer store with a
30-second lock-acquisition budget. A writer SHALL create and hold the
cross-platform lock while it verifies every observed byte and record, allocates
the next contiguous sequence, appends one canonical JSONL record, flushes, and
fsyncs. No trust cache or verified-prefix shortcut may replace full observed
stream verification.

Read-only verify/read calls SHALL NOT create a root, directory, ledger, lock
file, repair directory, or any other filesystem entry. Modules SHALL use
package-qualified sibling imports. Direct execution of the ledger script SHALL
bootstrap a private qualified package pinned to that script's actual plugin
root; it SHALL NOT resolve an unqualified ambient sibling module.

Every observed event line SHALL equal the exact canonical schema-v2
serialization followed by one LF byte. Leading, trailing, or interior
whitespace; CRLF; alternate key order; and alternate JSON escaping SHALL be
corruption even when they decode to the same value. Corruption SHALL block
normal append.

The hard limits are conjunctive capacity ceilings, not throughput guarantees:
a run ledger accepts at most 10,000 records, 16 MiB total, and 32 KiB per line.

#### Scenario: Empty ledger is inspected

- **WHEN** a caller verifies or reads a ledger whose root does not exist
- **THEN** the result is a valid empty stream and the filesystem is unchanged

#### Scenario: Older bytes were modified

- **WHEN** any earlier observed byte no longer satisfies canonical schema,
  sequence, run binding, predecessor digest, or record digest
- **THEN** verify reports corruption and normal append refuses the stream

#### Scenario: JSON meaning is unchanged but bytes differ

- **WHEN** an event line uses whitespace, CRLF, different key order, or an
  equivalent escape spelling
- **THEN** verify reports corruption and append leaves the stream unchanged

#### Scenario: Ledger CLI runs outside package import context

- **WHEN** the source script or an installed plugin-root `scripts/` copy is
  executed directly with `--help`
- **THEN** its qualified sibling contract import resolves from that exact
  plugin root and the command exits successfully

### Requirement: Integrity reports do not claim authentication

Every successful ledger/profile verification SHALL state that records are
unkeyed and user-writable, writer authenticity is not established, and
deletion of an unanchored suffix is not ruled out. Internal validity SHALL NOT
be reported as authenticity or completeness.

### Requirement: One delegation sample accepts many bound observations

Each unique delegation execution/result binding SHALL increment sample,
runtime-status, duration, token, and cost aggregates exactly once. Any number
of new peer, gate, verifier, or Owner observations for that delegation MAY
arrive in the first batch or later commits. Later accepted observations SHALL
increment only outcome, verification, finding, and regression aggregates.

Every observation SHALL carry the delegation run ID and SHA-256 digests of the
canonical full schema-v2 envelope and canonical full schema-v2 result. A later
observation is accepted only when its delegation ID, run ID, envelope digest,
and result digest match the durable original binding and its observation ID is
new.

Canonical comparison scope SHALL be the complete contract projection returned
by each contract's `to_dict`, serialized with sorted keys, ASCII escaping, and
compact separators.

#### Scenario: Two initial observers inspect one execution

- **WHEN** one batch submits the same envelope/result with two new, correctly
  bound observations
- **THEN** sample, status, duration, token, and cost counts increase once
- **AND** observation/finding/regression counts incorporate both observations

#### Scenario: A later verifier observes an existing execution

- **WHEN** a later commit resubmits the exact durable envelope/result with a
  new correctly bound verifier observation
- **THEN** only observation/finding/regression aggregates change

### Requirement: Every accepted or rejected submission is durable and replayable

Each profile commit SHALL persist every full submitted envelope, result, and
observation contract plus the deterministic decision for that source
submission. Replay from an empty state SHALL reclassify each submission,
reconstruct all delegation/observation indexes and profile aggregates, and
match every persisted snapshot and final state byte-for-byte.

An identical repeated observation ID SHALL produce a durable
`duplicate_observation_id` rejection. Conflicting reuse of a delegation ID,
run ID, envelope digest, result digest, or observation ID/content SHALL produce
one durable typed rejection decision naming every applicable reason. Rejected
submissions SHALL not change execution or accepted-observation aggregates, but
SHALL increment the corresponding durable conflict counters on the
known/original profile key. Same-batch and cross-commit events follow the same
classification.

#### Scenario: Duplicate observation is retried

- **WHEN** a committed observation ID is submitted again with identical
  content
- **THEN** the new commit persists the rejected source and decision, increments
  the original profile's duplicate-observation counter, and does not increment
  sample or accepted-observation counts

#### Scenario: Known delegation is reused with a different result

- **WHEN** a submitted source reuses a known delegation ID but its canonical
  result digest differs
- **THEN** a delegation-binding and result-digest conflict is persisted and
  attributed to the original profile key

### Requirement: Profile math exposes denominators and incompatible bases

Capability profiles SHALL be keyed by provider, model, role, and task class.
They SHALL store runtime-status-specific duration totals/sample counts. Token
aggregates SHALL be partitioned by runtime status, usage basis, and
reasoning-token semantics. Cost aggregates SHALL be partitioned by runtime
status and cost basis. No total combines completed with failed, timeout,
cancelled, invalid-output, or unavailable executions, and no total combines
reported with estimated evidence.

The sum of runtime-status counts SHALL equal sample count. Each nonzero status
duration aggregate SHALL have the same sample denominator as that status
count. Accepted sample count SHALL be less than or equal to accepted
observation count. Token and cost aggregate sample counts SHALL not exceed the
corresponding runtime-status sample count.

Profiles SHALL remain advisory: they do not grant permissions, waive gates,
select verifier independence, establish convergence, or override the Owner.

### Requirement: Persistent profile transitions carry explicit untrusted claims

A profile transition SHALL require the caller to provide
`claimed_terminal_status="verified"` and a safe
`untrusted_verification_ref`. These fields are explicitly untrusted in-band
controller/model claims. Their accepted shape does not prove the referenced
artifact exists, passed, or came from an independent verifier.

The store SHALL commit only when the durable current state digest equals the
frozen start digest and commit-time reduction of the retained source contracts
exactly matches the supplied shadow snapshot and decisions.

Every observed profile-commit line SHALL equal its exact canonical schema-v2
serialization followed by one LF byte. This comparison includes retained
sources and decisions; any whitespace, CRLF, alternate key order, or alternate
escaping SHALL be corruption and SHALL block another commit.

Profile history accepts at most 32 commits, 128 MiB total, 4 MiB per commit, 64
source submissions per commit, and 256 profile keys. These are capacity
ceilings, not latency or throughput promises.

#### Scenario: Same-batch conflicts survive replay

- **WHEN** a batch contains an accepted source, an identical duplicate, and a
  conflicting result binding
- **THEN** the store commits all three full sources and typed decisions
- **AND** rereading decisions and rebuilding from empty state produces the
  committed snapshot exactly

### Requirement: Torn-tail repair is explicit, digest-bound, and crash-replayable

Normal ledger append, read, and verify SHALL remain fail closed on every
corruption. Repair SHALL be an explicit operator-only API/CLI operation and
SHALL never run automatically.

Under the ledger lock, repair SHALL hash the exact current bytes and compare
that digest with the operator-supplied expected digest. Except for replay of an
already-written matching intent whose candidate digest is the current ledger,
digest mismatch SHALL refuse stale intent.

Repair SHALL accept only a non-newline final tail that is structurally
classifiable as truncated JSON after a fully valid prefix. It SHALL refuse a
newline-terminated invalid record, interior corruption, a complete
missing-newline record, semantic contract/digest corruption, an ambiguous or
wrong extractable next sequence, or malformed/conflicting repair metadata.
The incomplete-JSON classifier SHALL be bounded independently of the standard
recursive decoder. It SHALL apply schema-v2 depth, integer digit/magnitude,
finite float, constant, integer, and duplicate completed-object-key rules and
convert every parser/bound failure to `LedgerError`. Genuine terminal JSON,
string, and UTF-8-codepoint truncation SHALL remain classifiable.

Before replacing data, repair SHALL exclusively create, flush, and fsync an
immutable external intent recording schema/run binding, before digest, valid
prefix byte/record counts, discarded-tail digest/bytes, structural
classification, optional extractable sequence, candidate digest, optional
quarantine metadata, and a self-digest. It SHALL fsync the parent directory on
POSIX, optionally write/fsync explicitly selected raw-byte quarantine, prepare
and fsync the exact candidate, atomically replace the ledger, and fsync the
parent. Repair audit SHALL never be appended to the ledger being repaired.

Retry SHALL be idempotent before intent, after intent, after optional
quarantine, after candidate preparation, and after replacement. A current
ledger digest equal to the intent candidate digest establishes completed
replay.

Under the lock, every existing intent SHALL be validated against reachable
bytes, not only its self-digest. If current bytes are the before state, repair
SHALL recompute and compare the exact structural classification, prefix
byte/record counts, last record digest, candidate digest, discarded-tail
digest/count, next/extractable sequence, and quarantine selection. A prepared
or completed candidate SHALL be canonical and match exact
length/digest/record-count/last-digest/next-sequence relations. A later stream
SHALL begin with the exact candidate bytes and the complete current stream
SHALL verify canonically.

If quarantine is selected, its reference SHALL be exactly
`repair-quarantine/<before-sha256-hex>.bin`, its digest SHALL equal the
discarded-tail digest, and its bytes SHALL match the reachable tail. Absence is
allowed only while still in the pre-quarantine before state. Completed replay
SHALL require and verify the selected quarantine. Any impossible, malformed,
conflicting, orphaned, or stale relation SHALL block automated repair for
manual recovery.

#### Scenario: Operator intent is stale

- **WHEN** the exact current ledger digest is neither the supplied expected
  digest nor the candidate digest of its valid existing intent
- **THEN** repair refuses without changing the ledger

#### Scenario: Process stops after durable intent

- **WHEN** repair is retried with the same expected digest after intent fsync
- **THEN** the existing immutable intent is validated and reused, not replaced
  or duplicated

#### Scenario: Process stops after atomic replacement

- **WHEN** retry observes the valid intent and a ledger digest equal to the
  candidate digest
- **THEN** repair reports the transaction complete and leaves valid ledger
  bytes unchanged

### Requirement: Performance evidence is measured without weakening integrity

Focused tests SHALL build a deterministic preconstructed ledger at the
registered capacity sample, fully verify it, and compare the observation
against the 30-second writer lock budget. Sequential append timing SHALL be
recorded as an observation but SHALL not be a host-sensitive correctness
assertion. Capacity/latency documentation SHALL not advertise throughput
guarantees.

### Requirement: Fresh-checkout scaffold bundle preserves repository LF

The generated Codex project-scaffold bundle SHALL be rebuilt from the
LF-normalized `assets/project-scaffold` source. Every non-binary bundled text
entry SHALL be free of CRLF. Bundle load and rebuild checks SHALL fail directly
if a text entry embeds CRLF, even when its entry and tree digests were updated.

This bundle correction is a pre-existing fresh-checkout verification
prerequisite exposed by the LF worktree. It is not caused by delegation-ledger
runtime behavior.
