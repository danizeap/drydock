# Spec Delta: completion-integrity

Capability: completion-gate

First living spec for `hooks/completion_gate.py`, the `Stop` hook that nudges once when a packet looks claimed-done but is unverified. Read-only project scan; ships with the plugin; fires at every turn end. Loop-safety is paramount — the fail direction is always silent-allow (the archive gates remain the deterministic backstop).

## ADDED Requirements

### Requirement: Nudge only on claimed-done-but-unverified change
The hook SHALL emit a stop-blocking nudge for a packet only when ALL hold: the packet's implementation tasks look complete (no pending tasks, or the only pending task is the verification task), its `verification.md` is still Pending (missing, empty, or a `Result` of `Pending.`), and its content fingerprint changed since the session-start baseline (a new packet counts as changed). In every other case — pure conversation, work-in-progress, verification already filled, no change this session — it SHALL emit nothing and exit 0.

#### Scenario: Claimed-done but unverified fires
- **WHEN** a packet's tasks are completed this session and its verification.md is still Pending
- **THEN** the stop is blocked once with a reason naming the packet and pointing at `/drydock:verify`

#### Scenario: Pure conversation is never interrupted
- **WHEN** no packet content changed since session start
- **THEN** the hook emits nothing and the stop proceeds

#### Scenario: Work in progress is not nudged
- **WHEN** a packet changed but still has pending non-verification tasks
- **THEN** the hook emits nothing (the one-per-session budget is preserved for the real completion moment)

#### Scenario: Deleting verification.md does not evade
- **WHEN** a claimed-done packet's verification.md is missing or empty
- **THEN** it is treated as Pending and the nudge fires

### Requirement: Bounded, loop-safe nudging
The hook SHALL nudge at most once per packet and at most a fixed small number of times per session. It SHALL persist the updated nudge ledger atomically BEFORE emitting the block; if persistence fails for any reason, it SHALL emit nothing (a persistence failure degrades to silence, never repetition). Auto-compaction/resume SHALL NOT re-arm an already-spent nudge (the SessionStart stamp preserves the ledger). Any error, malformed input, or missing state SHALL result in exit 0.

#### Scenario: Second stop is silent after a nudge
- **WHEN** the same packet is evaluated again in the same session after it was nudged
- **THEN** the hook emits nothing

#### Scenario: Nudge not spoken if the ledger write fails
- **WHEN** the nudge ledger cannot be persisted
- **THEN** the hook emits nothing and exits 0 (no unguarded block that could loop)

#### Scenario: Malformed input never blocks a session
- **WHEN** stdin is empty or not valid JSON, or the session id/cwd is untrusted
- **THEN** the hook exits 0 and emits nothing

### Requirement: Self-heal when the baseline is absent
WHEN no valid session-state file exists at a stop (the orientation stamp never ran, or the file was removed/corrupted), the hook SHALL write a fresh baseline from the current project state and stay silent that turn, so every later turn of the session is covered rather than none.

#### Scenario: Missing state file self-heals silently
- **WHEN** the completion gate finds no valid state file
- **THEN** it stamps a baseline and emits nothing

### Requirement: State-file safety
The session-state file SHALL live in a per-user directory (not a world-writable temp dir), be named by a hash of the session id (no path traversal, no collision), and be read only when it is a regular file within a size cap and passes strict schema validation (matching session id, kebab packet names, bounded lists). A tampered, oversized, symlinked, corrupt, or foreign-session file SHALL be treated as missing. The nudge reason SHALL be a fixed template interpolating only a kebab-validated packet name.

#### Scenario: Hostile state file is treated as missing
- **WHEN** the state file is oversized, corrupt, or carries a different session id
- **THEN** the hook does not crash and does not emit a false nudge from it
