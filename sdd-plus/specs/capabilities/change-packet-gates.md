# Capability: change-packet-gates

Capability: change-packet-gates

## Purpose

The deterministic packet gates in `scripts/sdd.py` (`verify` and `archive`). They stop unfinished or undocumented work from being called complete or archived, using only what is in the working tree — no model judgment.

## Requirements

### Requirement: Placeholder gate catches shipped template forms
`verify` SHALL flag as unfilled any required artifact containing template placeholder residue in the forms the shipped templates actually use: whole-line `TBD` (with or without a list dash), checkbox `- [ ] TBD`, table-cell `| TBD |`, unreplaced `{{CHANGE_NAME}}`, and a verification.md whose `## Result` section still reads `Pending.` Placeholder residue quoted inside fenced blocks or inline `code` spans (i.e. a brief describing the forms) SHALL NOT be flagged.

#### Scenario: Pristine template packet fails verify
- **WHEN** `verify` runs on a packet whose verification.md and decision-log.md are untouched from the shipped templates
- **THEN** the exit code is 1 and the warning names those files

#### Scenario: Genuinely filled packet passes
- **WHEN** all required artifacts have real content and a non-Pending Result
- **THEN** `verify` exits 0 with no placeholder warning

#### Scenario: Quoted mentions do not false-positive
- **WHEN** a filled brief or decision-log quotes `| TBD |` or `- [ ] TBD` as an example inside inline `code` spans
- **THEN** `verify` does not flag that file

### Requirement: Archive fails closed on unattributable delta specs
WHEN a delta spec file under the change's `specs/` directory yields no valid kebab-case capability (missing `Capability:` line, angle-bracket placeholder value, or non-kebab value), `archive` SHALL exit with an error naming the file instead of silently skipping the sync gate; `--force` remains the explicit override.

#### Scenario: Placeholder capability line blocks archive
- **WHEN** a delta file's capability line is still an angle-bracket placeholder (e.g. `Capability: <capability-name>`)
- **THEN** `archive` (without --force) exits non-zero naming that file

### Requirement: Governed override
`archive --force` SHALL require an accompanying `--reason "<text>"`; bare `--force` SHALL be refused with guidance. When `--force` actually waives one or more gates, an auditable override record (date, the gate(s) waived, the reason) SHALL be appended to the change's `decision-log.md` before the packet is moved — so the record travels with the packet into `archive/`.

#### Scenario: Bare force is refused
- **WHEN** `sdd.py archive <name> --force` runs without `--reason`
- **THEN** it exits non-zero, telling the user that `--reason` is required, and moves nothing

#### Scenario: Forced override is recorded
- **WHEN** `sdd.py archive <name> --force --reason "<why>"` runs and one or more gates would otherwise fail
- **THEN** a `## Override` entry naming the waived gate(s) and the reason is appended to `decision-log.md`, and the packet is then archived

#### Scenario: Reason-only override without waived gates
- **WHEN** `--force --reason` is given but no gate actually fails
- **THEN** the archive proceeds and no override record is written (nothing was waived)

### Requirement: Exact requirement-name matching in the sync gate
The archive sync gate SHALL treat a delta's ADDED requirement as synced only when a living-spec heading's requirement name equals the delta's requirement name after whitespace/case normalization — substring containment SHALL NOT count.

#### Scenario: Substring no longer false-passes
- **WHEN** the delta adds `Session` and the living spec contains only `### Requirement: Session Expiry`
- **THEN** the gate reports `Session` as not synced

### Requirement: ADDED-section parsing respects section boundaries
The ADDED-requirement parser SHALL stop collecting at the next `##` heading of any kind, SHALL ignore fenced code blocks, and capability extraction SHALL do the same.

#### Scenario: Requirements under a Notes section are not ADDED
- **WHEN** a delta has `## ADDED Requirements` with one requirement followed by `## Notes` containing `### Requirement: Example`
- **THEN** only the first requirement is treated as ADDED

#### Scenario: Fenced capability lines are ignored
- **WHEN** a delta's only `capability:` text appears inside a fenced code block
- **THEN** the file yields no capability (and archive fails closed per the unattributable rule)

### Requirement: One shared readiness check feeds both the prompt and the gate
`verify` and `archive` SHALL determine archive-eligibility from ONE pure, read-only function (`archive_readiness`) returning the list of waivable blockers, so the ready prompt can never claim ready when archive would block. The waivable blockers SHALL be exactly: an unattributable delta (no valid `Capability:` line), a capability with no living spec, a delta requirement absent from its living spec, and an incomplete packet (pending tasks or unfilled placeholders).

#### Scenario: Prompt and gate agree
- **WHEN** `archive_readiness` returns a non-empty blocker list for a packet
- **THEN** `verify` does not print READY and `archive` refuses without `--force`, citing the same blockers

#### Scenario: A clean synced packet is archive-eligible
- **WHEN** every delta requirement is present in its living spec, the packet has no pending tasks and no unfilled placeholders
- **THEN** `archive_readiness` returns an empty list

### Requirement: The ready-at-green prompt fails toward needs-sync
On a green `verify` (no pending tasks, no unfilled placeholders), the tool SHALL print a ready line at the moment green is learned. It SHALL print `READY TO ARCHIVE` ONLY on positive confirmation that every delta requirement is synced into its living spec AND every delta requirement heading is the canonical machine-verifiable form. On any unsynced or non-machine-verifiable delta it SHALL instead direct the operator to `/drydock:sync` — it SHALL NOT infer READY from a merely empty blocker list.

#### Scenario: Ready only when synced and canonical
- **WHEN** verify runs green on a packet whose canonical delta requirements are all present in the living spec
- **THEN** it prints `READY TO ARCHIVE` with the archive command

#### Scenario: Canonical but unsynced routes to sync
- **WHEN** a delta's canonical requirement is not yet in the living spec
- **THEN** verify prints a `/drydock:sync` prompt, not READY

#### Scenario: Non-canonical grammar never reads as ready
- **WHEN** a delta authors a requirement as a non-canonical heading (e.g. `### R5 — <name>`)
- **THEN** verify warns the grammar is not machine-verifiable and does not print READY — closing the vacuous-pass hole where such a delta previously read as ready

#### Scenario: Archive is warned-but-permissive on non-canonical grammar (deferred boundary)
- **WHEN** `archive` runs on a packet whose delta uses non-canonical grammar and is otherwise complete
- **THEN** it prints the grammar warning but does NOT block on grammar alone and records no override — verify's prompt is deliberately stricter than the archive gate here; making archive fail toward needs-sync on grammar is a soft-REJECT and a separate Owner decision

### Requirement: Delta requirement grammar is linted at verify time
`verify` SHALL warn when a delta authors a requirement under `## ADDED Requirements` with a level-3 heading that is not the canonical `### Requirement: <name>` form, because such headings make the sync gate unverifiable (the requirement-presence check passes vacuously). The warning SHALL name at least one offending heading and point to `/drydock:sync`.

#### Scenario: Non-canonical heading is warned
- **WHEN** a delta contains `### R5 — <name>` under ADDED Requirements
- **THEN** verify emits a grammar warning naming that heading

#### Scenario: Canonical headings and scenarios are not warned
- **WHEN** a delta uses `### Requirement: <name>` with `#### Scenario:` sub-headings
- **THEN** verify emits no grammar warning

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
- **THEN** abandon warns that spec knowledge will not be harvested, naming the requirement or the delta file

#### Scenario: A collision leaves the packet untouched
- **WHEN** an archive target already exists for that date and name
- **THEN** abandon refuses before writing anything — the packet is not half-abandoned and no duplicate Override is appended

#### Scenario: Abandon requires a reason and refuses to combine with force
- **WHEN** `--abandon` is used without a non-empty `--reason`, or together with `--force`
- **THEN** the command refuses and moves nothing
