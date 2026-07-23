# Capability: codex-conductor

Capability: codex-conductor

## Purpose

The read-only multi-agent bridge (`scripts/conductor/codex_bridge.py`). It lets Drydock (the conductor) discover the locally-installed Codex core, read Codex's remaining quota, choose a model from that fuel, and delegate a bounded analysis/review task to Codex with schema-locked JSON output — for Claude to independently audit. It is **read-only by construction**: no code path mutates the repository, and secret-bearing content is refused before it leaves the machine. Mutating delegation is a separate concern (`codex-enforcement-bridge`). Proven live-fire on 2026-07-23 (see `sdd-plus/specs/multi-agent-orchestration-vision.md` §8).

## Requirements

### Requirement: Core discovery tracks the current install, never the stale binary
The conductor SHALL locate the Codex core by discovering the newest `codex.exe` under `%LOCALAPPDATA%\OpenAI\Codex\bin\*\`, and SHALL NOT use the `~/.codex/.sandbox-bin` copy. `discover_core()` returns a path on success and `None` when absent; absence SHALL NOT raise, and the orchestration layer surfaces it as a structured `{ok:false, stage:"discover"}`.

#### Scenario: Newest core wins
- **WHEN** two core binaries exist under the bin dir with different modification times
- **THEN** discovery returns the path of the most recently modified one

#### Scenario: Sandbox binary is never returned
- **WHEN** a `codex.exe` exists only under a `.sandbox-bin` path
- **THEN** discovery does not return it (it is outside the discovery root)

#### Scenario: Absence is structured, not an exception
- **WHEN** no core is found under the discovery root
- **THEN** `discover_core()` returns `None` without raising

### Requirement: The fuel gauge is read safely and always cleans up
Reading Codex quota SHALL return a structured result in every case and SHALL NOT leak the `app-server` subprocess.

#### Scenario: Successful read
- **WHEN** the gauge is read successfully
- **THEN** the result is `{ok:true, result:{...rateLimits...}}` including `primary.usedPercent` and `resetsAt`

#### Scenario: Operational failure is structured and reaped
- **WHEN** `app-server` fails to spawn, exits early, closes stdout, or does not respond within the timeout
- **THEN** the result is `{ok:false, stage, error, stderr}` — never a traceback — and the subprocess is terminated and reaped

#### Scenario: Non-object protocol line ignored
- **WHEN** a non-object JSON line appears on the protocol stream
- **THEN** it is ignored rather than crashing the reader

### Requirement: Delegation is structurally read-only
`delegate()` SHALL run Codex with a fixed safety flag set that no caller input can override, SHALL validate the model identifier as a bare token, and SHALL have no code path that writes into the repository.

#### Scenario: Read-only flags always present, escalation flags never
- **WHEN** any delegation argv is built
- **THEN** it contains `-s read-only` and none of `--dangerously-bypass-approvals-and-sandbox`, `workspace-write`, or `danger-full-access`

#### Scenario: Only prompt/schema/model/cwd are caller-controlled
- **WHEN** a caller invokes delegation
- **THEN** sandbox mode, ephemerality, and git-check flags are fixed by the conductor; the prompt is passed via stdin, never as argv

#### Scenario: Flag-shaped model refused
- **WHEN** the model identifier is not a bare token (e.g. contains a space or a leading `-`)
- **THEN** delegation is refused with `{ok:false, stage:"bad_model"}` before any spawn

#### Scenario: No repository mutation
- **WHEN** a delegation completes
- **THEN** the working root is a fresh temp dir that is cleaned up, and no file under the repository is created or modified

### Requirement: Secrets never leave the machine via delegation
The conductor SHALL refuse to delegate content whose source path is secret-bearing, reusing `hooks/protect_secrets.path_is_secret`, and SHALL fail closed if that checker cannot be loaded.

#### Scenario: Secret path refused before spawn
- **WHEN** `delegate_file` is asked to include content from a secret-bearing path (`.env`, key/credential files)
- **THEN** it returns `{ok:false, stage:"secret_guard"}` before reading the file or spawning Codex

#### Scenario: Ordinary file proceeds
- **WHEN** the content source is an ordinary project file
- **THEN** delegation proceeds

#### Scenario: Fail closed when the checker is unavailable
- **WHEN** the secret-path checker cannot be imported
- **THEN** `guard_outbound` refuses all delegation rather than egressing unchecked

### Requirement: Routing is a legible, fuel-aware policy
Model selection SHALL be a documented function of task weight and remaining Codex fuel.

#### Scenario: Heavy task with fuel above the floor
- **WHEN** the task is heavy and remaining fuel is above the conserve floor (15%)
- **THEN** the flagship model is selected

#### Scenario: Heavy task at or below the floor
- **WHEN** the task is heavy but fuel is at or below the floor
- **THEN** a workhorse model is selected to conserve the tank

#### Scenario: Light task
- **WHEN** the task is light
- **THEN** a workhorse model is selected regardless of fuel

### Requirement: No live quota spent by the test suite
Automated tests SHALL prove the above without invoking the real Codex service; any live smoke test SHALL be opt-in and excluded from CI.

#### Scenario: CI spends no quota
- **WHEN** the test suite runs in CI
- **THEN** it uses a fake Codex stand-in (invoked through the real subprocess path) and spends no account quota

#### Scenario: Live test is opt-in
- **WHEN** a developer sets `DRYDOCK_CODEX_LIVE=1`
- **THEN** a single real round-trip may run locally; otherwise it is skipped
