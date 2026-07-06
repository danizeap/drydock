# Capability: session-orientation

Capability: session-orientation

## Purpose

`hooks/session_orient.py`, the `SessionStart` hook that orients the agent to Drydock project state and probes guardrail liveness. Read-only; ships with the plugin; fires in every session. It can only ever add context — never block, fail, or materially slow a session.

## Requirements

### Requirement: Silent outside a Drydock project
The hook SHALL emit nothing and exit 0 whenever the session is not inside a Drydock project. Project discovery SHALL be bounded (not an unbounded upward walk): the closest ancestor of `cwd` that has both an `sdd-plus/` directory and a Drydock marker (`AGENTS.md` or `sdd-plus/protocols/`), stopping at the git-repo root or `$HOME`, and excluding the plugin's own install tree and any `assets/project-scaffold` template. `cwd` is untrusted — if it is missing, empty, non-absolute, or not an existing directory, the hook SHALL no-op (never falling back to the process working directory).

#### Scenario: Non-Drydock directory is silent
- **WHEN** SessionStart fires with a `cwd` that has no Drydock project at or above it
- **THEN** the hook emits no output and exits 0

#### Scenario: Untrusted cwd is silent
- **WHEN** the SessionStart payload has a missing/empty/relative/nonexistent `cwd`
- **THEN** the hook emits no output and exits 0 (no process-cwd fallback)

#### Scenario: Real project is oriented
- **WHEN** SessionStart fires with `cwd` inside a Drydock project
- **THEN** the hook emits `additionalContext` describing PROJECT_CONTEXT state, active packets, and the guardrail verdict

### Requirement: Never blocks or fails a session
The hook SHALL always exit 0. Any internal error — including a `SystemExit` from any helper, a subprocess timeout, or malformed stdin — SHALL be caught and result in exit 0 with no emitted context. The guardrail probe SHALL run with a bounded per-probe timeout.

#### Scenario: Internal exception still exits 0
- **WHEN** the hook body raises any exception (including SystemExit)
- **THEN** it exits 0 and emits nothing

#### Scenario: Malformed stdin is safe
- **WHEN** stdin is empty or not valid JSON
- **THEN** the hook exits 0 and emits nothing

### Requirement: Emits only derived, non-sensitive signals
The emitted `additionalContext` SHALL contain only derived signals — enum states (missing/template/real), integer counts, boolean flags, and kebab-validated packet names — never raw file content, file excerpts, or absolute filesystem paths. Output SHALL be size-capped.

#### Scenario: No file content or absolute paths leak
- **WHEN** the project's files contain sensitive text or the project sits at a revealing absolute path
- **THEN** the emitted context contains no file excerpts and no absolute paths, only derived states/counts/names

### Requirement: Honest guardrail liveness probe
The hook SHALL report a guard as "live" only when running that guard script under the current interpreter exits exactly 2 on a destructive probe payload, the guard's expected block message appears on stderr, AND a benign control payload exits 0. Any other outcome SHALL be reported as "degraded" (named) or "unverified". The verdict SHALL claim only what it verified (the guard SCRIPT blocks under a probe), and a separate static check SHALL report whether `hooks.json` registers the guards. The probe SHALL never claim the wired in-session PreToolUse chain is protected. The verdict SHALL be freshly measured each session (never cached).

#### Scenario: Live only on a genuine block
- **WHEN** a guard exits 2 with its expected message on the destructive probe and exits 0 on the benign control
- **THEN** that guard is reported "live"

#### Scenario: Wrong-reason exit 2 is not "live"
- **WHEN** a guard exits 2 without the expected block message (e.g. a SystemExit/argparse error) or blocks the benign control
- **THEN** it is reported "degraded", never "live"

#### Scenario: Missing guard script is degraded
- **WHEN** a guard script is absent
- **THEN** it is reported "degraded (script missing)", never "live"
