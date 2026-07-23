# Capability (delta): codex-conductor

Capability: codex-conductor

Read-only multi-agent delegation — Drydock (the conductor) discovers the current Codex core, reads Codex's remaining quota, and delegates a bounded analysis/review task to Codex with schema-locked output, without any ability to mutate the repository or leak secrets.

Status: delta (new capability). Introduced by change `conductor-mvp`. Scope: read-only. Mutating delegation is explicitly NOT part of this capability (see `codex-enforcement-bridge`).

## ADDED Requirements

### R1 — Core discovery tracks the current install, never the stale binary
The conductor MUST locate the Codex core by discovering the newest `codex.exe` under `%LOCALAPPDATA%\OpenAI\Codex\bin\*\`, and MUST NOT use the `~/.codex/.sandbox-bin` copy. Absence MUST surface as a structured failure, not an exception.

- **WHEN** two core binaries exist under the bin dir with different modification times, **THEN** discovery returns the path of the most recently modified one.
- **WHEN** the sandbox binary is the only `codex.exe` present under `.sandbox-bin`, **THEN** discovery does NOT return it (it is outside the discovery root).
- **WHEN** no core is found, **THEN** `discover_core()` returns `None` (its success value is a path; absence is `None`), and the orchestration layer surfaces that as a structured `{ok: false, stage: "discover"}`; neither path raises.

### R2 — The fuel gauge is read safely and always cleans up
Reading Codex quota MUST return a structured result in every case — success or failure — and MUST NOT leak the `app-server` subprocess.

- **WHEN** the gauge is read successfully, **THEN** the result is `{ok: true, result: {...rateLimits...}}` including `primary.usedPercent` and `resetsAt`.
- **WHEN** `app-server` fails to spawn, exits early, closes stdout, or does not respond within the timeout, **THEN** the result is `{ok: false, stage, error, stderr}` — never a traceback — and the subprocess is terminated and reaped.
- **WHEN** a non-object JSON line appears on the protocol stream, **THEN** it is ignored rather than crashing the reader.

### R3 — Delegation is structurally read-only
`delegate()` MUST run Codex with a fixed safety flag set that no caller input can override, and MUST have no code path that writes into the repository.

- **WHEN** any delegation is invoked, **THEN** the emitted argv contains `-s read-only` and contains none of `--dangerously-bypass-approvals-and-sandbox`, `workspace-write`, or `danger-full-access`.
- **WHEN** a caller supplies a prompt, schema, model, and working dir, **THEN** those are the ONLY caller-controlled inputs; the sandbox mode, ephemerality, and git-check flags are fixed by the conductor.
- **WHEN** delegation completes, **THEN** the return value carries the schema-conforming `result` and the turn `usage`, and no file under the repository has been created or modified by the delegation.

### R4 — Secrets never leave the machine via delegation
The conductor MUST refuse to delegate content whose source path is secret-bearing, reusing the plugin's `path_is_secret`.

- **WHEN** delegation is asked to include content from a path matching the secret-path rules (`.env`, key/credential files), **THEN** the delegation is refused before any subprocess is spawned.
- **WHEN** the content source is an ordinary project file, **THEN** delegation proceeds.

### R5 — Routing is a legible, fuel-aware policy
Model selection MUST be a documented function of task weight and remaining Codex fuel, not a hidden default.

- **WHEN** the task is heavy and Codex remaining fuel is above the conserve floor, **THEN** the flagship model is selected.
- **WHEN** the task is heavy but fuel is at or below the floor, **THEN** a workhorse model is selected to conserve the tank.
- **WHEN** the task is light, **THEN** a workhorse model is selected regardless of fuel.

### R6 — No live quota is spent by the test suite
Automated tests MUST prove R1–R5 without invoking the real Codex service; any live smoke test MUST be opt-in and excluded from CI.

- **WHEN** the test suite runs in CI, **THEN** it uses a fake Codex stand-in and spends no account quota.
- **WHEN** a developer opts into the live smoke test via the documented flag, **THEN** a single real round-trip may run locally.
