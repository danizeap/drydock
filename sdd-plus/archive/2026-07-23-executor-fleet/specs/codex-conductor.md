# Capability (delta): codex-conductor

Capability: codex-conductor

Extends the conductor into a FLEET manager: a pluggable executor interface with Codex proven and Kimi staged, plus a user-choosable stack. The honesty guarantee — an unverified executor can never run — is the load-bearing property.

## ADDED Requirements

### R13 — Pluggable executors with a proven/staged distinction
The conductor SHALL expose executors through a common interface (`available`, `read_remaining`, `status`) with `CodexExecutor` verified (wrapping the proven `codex_bridge`) and `KimiExecutor` staged (`verified=False`). `available()` (presence) SHALL be separate from `verified` (proven on this machine).

- **WHEN** `CodexExecutor` runs on a machine with a discoverable Codex core
- **THEN** it reports available + verified and reads real remaining fuel

### R14 — A staged executor can never run or be reported usable
An unverified executor SHALL NOT appear in the fleet's `usable` set and SHALL refuse to read fuel or execute, EVEN IF present on the machine. Presence is `staged`, distinct from usable.

- **WHEN** Kimi is not installed
- **THEN** it is neither usable nor staged

- **WHEN** Kimi IS present but unverified
- **THEN** it is reported `staged` (not `usable`) and `read_remaining()` raises `ExecutorUnverified`

### R15 — Fleet status is honest about the conductor's own quota
`fleet_status()` SHALL list Claude (the conductor) separately with a note that its own quota is not machine-readable (human-tracked), and SHALL report each executor's usable/staged state.

- **WHEN** the fleet status is read
- **THEN** Claude is present as the conductor (human-tracked), and each executor shows available/verified with fuel only when both are true

### R16 — The Owner chooses the stack
The active executor set SHALL be configurable (`DRYDOCK_EXECUTORS`), defaulting to auto-detection of all known executors, so the Owner can run Claude alone, +Codex, +Kimi, or all three.

- **WHEN** `DRYDOCK_EXECUTORS=codex`
- **THEN** only Codex is considered
