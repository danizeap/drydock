# Spec Delta: autopilot-floor

Capability: change-packet-gates

Adds override governance to the existing packet gates. Merges into the living `change-packet-gates` capability spec.

## ADDED Requirements

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
