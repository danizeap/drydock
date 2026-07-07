# Spec Delta: packet-guard (owner-brief change)

Capability: packet-guard

## ADDED Requirements

### Requirement: Generated status file is deny-protected
The guard SHALL deny Write/Edit/MultiEdit calls and Bash first-level write targets whose basename casefolds to `owner_status.md` within a Drydock project — regardless of packet state, since the file is a generated artifact whose hand-editing is never governed work — with a fixed-template reason naming the recovery path (`/drydock:brief` regenerates it). The engine's own `--write-status` path is script-internal I/O and is unaffected. Test/fixture/example/docs-directory path segments SHALL suppress this deny like every other deny class. This deny SHALL append a distinct ledger category and SHALL follow the guard's universal contracts (silent-allow on any error, never `updatedInput`).

#### Scenario: Freelance green status is stopped
- **WHEN** an agent writes OWNER_STATUS.md directly, with or without an active packet
- **THEN** the write is denied and the reason points at /drydock:brief

#### Scenario: Fixtures stay editable
- **WHEN** tests/fixtures/OWNER_STATUS.md is edited
- **THEN** the guard does not deny
