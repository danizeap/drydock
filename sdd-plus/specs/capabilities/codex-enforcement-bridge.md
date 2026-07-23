# Capability: codex-enforcement-bridge

Capability: codex-enforcement-bridge

## Purpose

Drydock's deterministic deny-guards (destructive git + secret-bearing writes) enforce under **Codex**, not only inside Claude Code, plus an agent-agnostic **git pre-commit** backstop. A scaffolded `.codex/hooks/drydock_guard.py` dispatcher (`assets/project-scaffold/.codex/`) resolves the installed Drydock plugin's `hooks/` and reuses `git_safety` + `protect_secrets` unchanged — Codex's hook payload is Claude-compatible (`tool_name` + `tool_input`; shell command as `tool_input.command`). It denies via Codex's `permissionDecision: deny` protocol (exit 0) and **fails open on any error**. Scope is the stateless critical floor; `packet_guard` and mutating-workflow governance are out of scope.

### Known limitations (v1)
- Native `apply_patch` is covered; a patch smuggled through a shell command (heredoc) is caught only by the git hook at commit time, not at write time.
- A pure-Codex install (no plugin) cannot reach the guards → the dispatcher fails open; the git pre-commit hook remains the secrets backstop.

## Requirements

### Requirement: Codex deny-guards fire via the JSON protocol
The `.codex/` dispatcher SHALL run on Codex `PreToolUse` for shell tools, `apply_patch`, and file-edit tools, and SHALL deny a destructive-git or secret-write action by emitting `hookSpecificOutput.permissionDecision: "deny"` on stdout with exit 0, reusing the plugin's `git_safety`/`protect_secrets` (single source of truth). Edit-path detection SHALL be case-robust.

#### Scenario: Destructive git denied
- **WHEN** Codex issues `{"tool_name":"Bash","tool_input":{"command":"git reset --hard HEAD~3"}}`
- **THEN** the dispatcher emits a JSON `permissionDecision: deny` and exits 0

#### Scenario: Secret write via shell denied
- **WHEN** Codex issues `echo K=V > .env` or PowerShell `Set-Content -Path .env -Value ...`
- **THEN** the dispatcher denies via the JSON protocol

#### Scenario: Native apply_patch secret creation denied
- **WHEN** Codex issues an `apply_patch` adding/updating a secret-bearing file (`*** Add File: .env`)
- **THEN** the dispatcher denies via the JSON protocol

### Requirement: Benign actions and reads pass silently
The dispatcher SHALL produce no output and exit 0 for actions that are not destructive-git and do not write a secret path (including secret reads).

#### Scenario: Benign or read passes
- **WHEN** Codex issues `ls -la`, `cat .env` (a read), a `Write` to `src/app.py`, or an `apply_patch` adding `notes.txt`
- **THEN** the dispatcher exits 0 with no output

### Requirement: Fail open, never brick a session
The dispatcher SHALL exit 0 with no output on ANY error — malformed input, non-dict payload/tool_input, unresolvable plugin, or a guard exception.

#### Scenario: Malformed input fails open
- **WHEN** the stdin payload is not valid JSON
- **THEN** the dispatcher exits 0 with no output

#### Scenario: Unresolvable plugin fails open
- **WHEN** the Drydock plugin cannot be resolved (pure-Codex install)
- **THEN** the dispatcher exits 0 with no output (the git pre-commit hook remains the secrets backstop)

### Requirement: Agent-agnostic git pre-commit backstop
A git `pre-commit` hook SHALL block committing a staged secret-bearing file, firing for Codex, Claude Code, AND a human `git commit`. It SHALL be self-contained (plugin `path_is_secret` or an inline fallback with no drift from `protect_secrets._SECRET`). Fail-mode: cannot-list-staged-files fails OPEN (never brick committing); secret-detection failure fails CLOSED (block).

#### Scenario: Staged secret blocked
- **WHEN** a `.env`/key/credential file is staged and `pre-commit` runs
- **THEN** it exits non-zero and names the offending file

#### Scenario: Ordinary file allowed
- **WHEN** only ordinary files (e.g. `README.md`) are staged
- **THEN** `pre-commit` exits 0

### Requirement: Installed by init, gated on `.git/` changes
`/drydock:init-project` SHALL copy the `.codex/` bridge and offer to install the git hook, requiring Owner approval before writing under `.git/hooks/` and never overwriting an existing `pre-commit`.

#### Scenario: Init wiring
- **WHEN** init runs in a project
- **THEN** the `.codex/` bridge is copied and the git-hook install is offered with an explicit Owner-approval gate on `.git/hooks/`
