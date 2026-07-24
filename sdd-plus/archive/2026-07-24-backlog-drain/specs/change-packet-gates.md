# Capability (delta): change-packet-gates

Capability: change-packet-gates

Adds the tooling to drain a backlog of stalled packets: a read-only triage that buckets every active packet, and an honest `--abandon` disposition for work that was never verified.

## ADDED Requirements

### Requirement: Triage buckets every active packet read-only
`triage` SHALL classify every active packet into exactly one bucket — ARCHIVE-READY, NEEDS-SYNC, CLAIMED-DONE-UNVERIFIED, IN-PROGRESS, or UNKNOWN — using the same predicates as verify and archive, and SHALL print a per-bucket next action. It SHALL write nothing. Classification SHALL be robust: an error on one packet (e.g. a missing required file) SHALL bucket that packet, never abort the batch.

#### Scenario: Each state buckets correctly
- **WHEN** triage runs over packets that are respectively verified+synced, canonically-authored-but-unsynced, tasks-done-but-verification-pending, and tasks-pending
- **THEN** they are labelled ARCHIVE-READY, NEEDS-SYNC, CLAIMED-DONE-UNVERIFIED, and IN-PROGRESS

#### Scenario: A broken packet does not abort the sweep
- **WHEN** a packet directory is missing required files
- **THEN** triage buckets it (IN-PROGRESS / UNKNOWN) and still reports every other packet

### Requirement: Abandon records the absence of a verification, never a pass
`archive --abandon --reason "<why>"` SHALL archive a packet as never-verified: it SHALL write the verification `## Result` to a normalized `Abandoned <date> — never verified` record (SHALL NOT synthesize a PASS, and SHALL NOT leave a stray verdict on a malformed Result heading), SHALL log an Override, SHALL warn when it buries spec knowledge not in the living specs — canonical unsynced requirements AND deltas whose sync cannot be verified (non-canonical grammar or no `Capability:` line) — and SHALL only MOVE the packet (never delete). The collision check SHALL precede any mutation, so a name clash leaves the packet intact. `--abandon` SHALL require a non-empty `--reason` and SHALL be mutually exclusive with `--force`.

#### Scenario: Abandon writes an honest result and moves the packet
- **WHEN** a packet is abandoned with a reason
- **THEN** its Result reads `Abandoned … never verified`, an Override is recorded, and it is moved to `archive/` — with no PASS anywhere, including no stray verdict left on a malformed heading

#### Scenario: Abandon warns before burying any unsynced spec knowledge
- **WHEN** the abandoned packet has a canonical delta requirement absent from its living spec, or a delta whose grammar/attribution makes sync unverifiable
- **THEN** abandon warns that spec knowledge will not be harvested, naming the requirement or the delta file — abandon is not quieter than triage or verify about the same deltas

#### Scenario: A collision leaves the packet untouched
- **WHEN** an archive target already exists for that date and name
- **THEN** abandon refuses before writing anything — the packet is not half-abandoned and no duplicate Override is appended

#### Scenario: Abandon requires a reason and refuses to combine with force
- **WHEN** `--abandon` is used without a non-empty `--reason`, or together with `--force`
- **THEN** the command refuses and moves nothing
