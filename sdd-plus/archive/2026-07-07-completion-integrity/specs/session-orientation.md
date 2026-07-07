# Spec Delta: completion-integrity

Capability: session-orientation

Adds one duty to the existing session-orientation capability: stamping the session-state file the Stop-hook completion gate reads. All existing session-orientation requirements (silent-outside-Drydock, never-blocks, derived-signals-only, honest guardrail probe) are unchanged.

## ADDED Requirements

### Requirement: Session-state stamp for the completion gate
On SessionStart in a Drydock project, the hook SHALL best-effort write a per-session state file recording the current packet fingerprints as the session-start baseline, using the same shared discovery and fingerprint logic as the Stop-hook completion gate (so the two can never drift). The stamp SHALL be best-effort: any failure is swallowed and never affects orientation output, and the project tree SHALL remain read-only (the state file lives in a per-user directory). On `resume`/`compact` for a session whose state file already exists, the hook SHALL preserve the existing baseline and nudge ledger rather than resetting them (auto-compaction must not re-arm the nudge); only `startup`/`clear`, or the absence of a valid file, produces a fresh baseline.

#### Scenario: Startup stamps a fresh baseline
- **WHEN** SessionStart fires with source `startup` in a Drydock project
- **THEN** a state file with the current packet fingerprints and an empty nudge ledger is written

#### Scenario: Compact preserves the ledger
- **WHEN** SessionStart fires with source `compact` and a valid state file for the session already exists
- **THEN** the existing baseline and nudge ledger are preserved unchanged

#### Scenario: Stamp failure never affects orientation
- **WHEN** the state file cannot be written
- **THEN** orientation context is still emitted and the hook exits 0
