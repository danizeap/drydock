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

### Requirement: In-session review CLI with structured outcomes
`scripts/conductor/review.py` SHALL delegate a read-only review of one or more files to Codex and print a structured JSON result for EVERY outcome — never a bare traceback. It SHALL reuse the conductor primitives, refuse secret-bearing paths (given paths AND their realpaths), frame file content as untrusted data (prompt-injection defense), and enforce per-file and total byte caps.

#### Scenario: Ordinary file reviewed
- **WHEN** the target is an ordinary file and Codex is available
- **THEN** the CLI prints `{ok: true, gauge, route, delegation.result}` and exits 0

#### Scenario: Secret path refused (incl. via realpath)
- **WHEN** a target path or its realpath is secret-bearing
- **THEN** the CLI prints `{ok: false, stage: "secret_guard"}` and sends nothing

#### Scenario: Every failure is structured
- **WHEN** Codex is absent, a file is missing, exceeds the size cap, or a read fails
- **THEN** the CLI prints `{ok: false, stage: "discover"|"missing_file"|"too_large"|"read_error"}` rather than raising

### Requirement: The review command audits, never rubber-stamps
The `/drydock:codex-review` command SHALL treat Codex's findings as input to an independent audit (confirm/refute/refine + additions from wider context), present a synthesis with Codex's remaining fuel noted, never send secret-bearing files, and never modify the repository.

#### Scenario: Findings are audited before presentation
- **WHEN** Codex returns findings
- **THEN** Claude verifies each (CONFIRM/REFUTE/REFINE) before presenting, and Codex's output is never treated as authoritative

### Requirement: Mutating delegation is isolated to a worktree, never the base branch
`scripts/conductor/mutate.py` SHALL run Codex with sandbox `workspace-write` confined to a dedicated worktree on a fresh `codex/…` branch from `base`. It SHALL NOT write to the Owner's branch or working tree, and SHALL be the only conductor path that enables writes (the read-only `delegate()` lock is unchanged).

#### Scenario: Writes are contained
- **WHEN** a mutating task runs
- **THEN** Codex's changes appear only in the isolated worktree/branch; the base branch HEAD is unadvanced and the main working tree is unmodified

### Requirement: The merge gate is applicability-first; N/A is never a failure
Before pass/fail, the gate SHALL decide whether it applies. Docs/config-only → test gate N/A (clean pass). Code/behavior change → green tests required (red or not-run is a hard block). N/A SHALL be distinct from FAIL.

#### Scenario: Docs-only is N/A
- **WHEN** the change touches only docs/config
- **THEN** the verdict is `n/a` with `clears: true` — not a failure

#### Scenario: Code needs green
- **WHEN** the change touches code and tests are red or were not run
- **THEN** the verdict is `red`/`blocked` with `clears: false`

### Requirement: No auto-merge; structured verdict for review
`mutate.py` SHALL NEVER merge. It SHALL return `{worktree, branch, diff, files, tests, gate, clears_gate, merged: false, note}` for Claude to review and merge deliberately; clearing the gate is necessary, not sufficient. Every outcome SHALL be structured (no bare traceback).

#### Scenario: Nothing merges automatically
- **WHEN** a mutating delegation completes
- **THEN** the result reports `merged: false` and carries the diff + gate verdict; the worktree is kept when reviewable and cleaned up on empty/failed delegation

### Requirement: Cleanup is blast-radius-bounded
Worktree cleanup SHALL remove only the temp worktree and a branch whose name begins with `codex/`; it SHALL never delete any other branch.

#### Scenario: Non-codex branch is safe
- **WHEN** cleanup is asked to delete a non-`codex/` branch
- **THEN** that branch is left intact

### Requirement: Pluggable executors with a proven/staged distinction
The conductor SHALL expose executors through a common interface (`available`, `read_remaining`, `status`), with `CodexExecutor` verified (wrapping `codex_bridge`) and additional executors (e.g. `KimiExecutor`) staged. `available()` (presence) SHALL be separate from `verified` (proven on this machine).

#### Scenario: Codex reads real fuel
- **WHEN** `CodexExecutor` runs where a Codex core is discoverable
- **THEN** it reports available + verified and reads real remaining fuel

### Requirement: A staged executor can never run or be reported usable
An unverified executor SHALL NOT appear in the fleet `usable` set and SHALL refuse to read fuel or execute, EVEN IF present on the machine.

#### Scenario: Present-but-unverified is staged, not usable
- **WHEN** a staged executor (Kimi) is present but unverified
- **THEN** it is reported `staged`, never `usable`, and its run/read path raises `ExecutorUnverified`

### Requirement: Honest fleet status + Owner-chosen stack
`fleet_status()` SHALL list Claude (the conductor) separately as human-tracked (its quota is not machine-readable), report each executor's usable/staged state, and honor an Owner-configured stack (`DRYDOCK_EXECUTORS`) defaulting to auto-detection (Claude alone / +Codex / +Kimi / all three).

#### Scenario: Stack is configurable
- **WHEN** `DRYDOCK_EXECUTORS=codex`
- **THEN** only Codex is considered; Claude remains the human-tracked conductor

### Requirement: Deterministic, read-only handoff state
`handoff.py::gather_state()` SHALL capture — without mutating the repo — the branch, HEAD, active change packets, open `codex/` worktrees, and the executor `fleet_status()`. Read failures SHALL degrade to benign values, never a traceback.

#### Scenario: State is gathered read-only
- **WHEN** `gather_state()` runs
- **THEN** it returns branch/HEAD/active packets/open codex worktrees/fleet and makes no changes

### Requirement: HANDOFF.md relay, re-verified on the way in
`write_handoff()` SHALL render a fixed-shape `HANDOFF.md` (where-we-are / fleet fuel / next step / notes) where only the next step + notes are human-supplied; `read_handoff()` returns it or None. The `/drydock:handoff` command SHALL instruct the incoming leader to reconstruct from live reality — HANDOFF.md never overrides `git`/`sdd.py status`.

#### Scenario: Incoming leader re-verifies
- **WHEN** a leader writes a handoff and another resumes from it
- **THEN** HANDOFF.md carries deterministic state + a one-line next step, and the incoming leader re-verifies against reality before acting

### Requirement: Fuel-aware fleet advice; Claude human-tracked
`fleet_recommendation()` SHALL list each usable tank's fuel/reset, flag a low tank (`<15%`), prefer spending the tank closest to its reset (protect the far one), and always note Claude as human-tracked.

#### Scenario: Spend the near-reset tank
- **WHEN** two tanks are usable with different reset horizons
- **THEN** the advice prefers spending the nearer-reset tank and protecting the other; Claude is noted as human-tracked
