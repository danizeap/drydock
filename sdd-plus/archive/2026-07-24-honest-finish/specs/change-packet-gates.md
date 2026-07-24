# Capability (delta): change-packet-gates

Capability: change-packet-gates

Makes finishing a packet near-free and honest: one shared readiness check that `verify`'s prompt and `archive`'s gate both consult, a well-timed ready-at-green prompt, and a delta-grammar lint that closes a vacuous-pass hole.

## ADDED Requirements

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
