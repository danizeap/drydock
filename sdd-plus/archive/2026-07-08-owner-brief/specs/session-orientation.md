# Spec Delta: session-orientation (owner-brief change)

Capability: session-orientation

## ADDED Requirements

### Requirement: OWNER_STATUS staleness sentinel
WHEN a Drydock project contains an OWNER_STATUS.md whose embedded project fingerprint no longer matches the freshly computed fingerprint, the orientation hook SHALL add a single line to its (already capped) additional context — phrased as a trust instruction to the agent ("do not cite it as current; if the Owner asks about status, run /drydock:brief in the Owner's language"), not as a prompt to volunteer a refresh — and SHALL emit it only when the session source is startup or clear, so resume and auto-compaction never re-arm it. The check SHALL be read-only toward the project tree, size-capped, and fail-silent: a missing, oversized, or unparseable OWNER_STATUS.md produces no sentinel line and no error. A matching fingerprint SHALL produce no line.

#### Scenario: Stale status file yields one trust instruction at true session start
- **WHEN** project state has changed since OWNER_STATUS.md was generated and the source is startup
- **THEN** orientation context includes one line telling the agent not to cite the file as current

#### Scenario: Resume and compaction do not re-arm the sentinel
- **WHEN** the session source is resume or compact
- **THEN** no sentinel line is emitted regardless of staleness

#### Scenario: Fresh or absent status file stays silent
- **WHEN** OWNER_STATUS.md matches current state or does not exist
- **THEN** no sentinel line is emitted

### Requirement: Probe marking and session coverage marker
The orientation hook SHALL set `DRYDOCK_PROBE=1` in the environment of every guardrail liveness probe child process, so probe denies are excluded from the event ledger while the probed verdict behavior remains byte-identical. Once per NEW session (source startup or clear — resume and compaction never re-count) it SHALL best-effort append a single `session` marker event to the per-user ledger (establishing machine coverage bounds for the Owner brief); this write targets the per-user state directory only — the project tree remains read-only — and every failure is silent.

#### Scenario: Probes prove blocking without polluting history
- **WHEN** orientation probes git-safety and secrets guards
- **THEN** both still report live via genuine blocks and the ledger gains no deny events

#### Scenario: Session coverage accrues silently
- **WHEN** a session starts in a Drydock project
- **THEN** one session marker is appended best-effort and orientation output is unchanged even if the append fails
