# Capability (delta): codex-enforcement-bridge

Capability: codex-enforcement-bridge

Drydock's deterministic deny-guards (destructive git, secret-bearing writes) enforce under Codex — not only inside Claude Code — plus an agent-agnostic git pre-commit backstop. Reuses the plugin's guards via a `.codex/` dispatcher that speaks Codex's `permissionDecision: deny` protocol and fails open on any error. Scope: the stateless critical floor (secrets + destructive git). packet_guard and mutating-workflow governance are out of scope.

### Known limitations (v1)

- **Native `apply_patch` is covered; `apply_patch` delivered as shell text is not.** A patch issued through Codex's native `apply_patch` tool is parsed and denied at PreToolUse. But if a patch body is smuggled through a shell command (e.g. `apply_patch <<EOF … *** Add File: .env … EOF`), the PreToolUse layer sees only the shell command and does not parse the patch body, so a secret-bearing write there is caught by the git pre-commit hook at **commit time**, not at write time — the secret may transiently land on disk before the commit is attempted. This is an accepted v1 gap of the stateless floor.
- **Fail-open when the plugin is unresolvable.** A pure-Codex install (no Drydock plugin) cannot reach the guards, so the dispatcher fails open; the git pre-commit hook remains the agent-agnostic secrets backstop. A self-contained bundled guard is a fast-follow.

## ADDED Requirements

### R1 — Codex deny-guards fire via the JSON protocol
A `.codex/hooks/drydock_guard.py` dispatcher SHALL run on Codex `PreToolUse` for shell tools (`Bash`/`PowerShell`), `apply_patch`, and file-edit tools, and SHALL deny a destructive-git or secret-write action by emitting `hookSpecificOutput.permissionDecision: "deny"` on stdout with exit 0 — the same protocol the plugin's own hooks emit. It SHALL reuse the plugin's `git_safety` and `protect_secrets` guards (single source of truth), resolved from the installed plugin.

- **WHEN** Codex issues a `Bash` call `{"command": "git reset --hard HEAD~3"}`
- **THEN** the dispatcher emits a JSON `permissionDecision: deny` and exits 0

- **WHEN** Codex issues a shell call that writes a secret path (`echo K=V > .env`, or PowerShell `Set-Content -Path .env ...`)
- **THEN** the dispatcher denies via the JSON protocol

- **WHEN** Codex issues an `apply_patch` that adds/updates a secret-bearing file (e.g. `*** Add File: .env`)
- **THEN** the dispatcher denies via the JSON protocol

### R2 — Benign actions and reads pass silently
The dispatcher SHALL produce no output and exit 0 for actions that are not destructive-git and do not write a secret path.

- **WHEN** Codex issues `{"command": "ls -la"}`, `{"command": "cat .env"}` (a read), a `Write` to `src/app.py`, or an `apply_patch` adding `notes.txt`
- **THEN** the dispatcher exits 0 with no output

### R3 — Fail open, never brick a session
The dispatcher SHALL exit 0 with no output on ANY error — malformed input, unresolvable plugin, or a guard exception. A guardrail bug must never block a Codex session.

- **WHEN** the stdin payload is not valid JSON
- **THEN** the dispatcher exits 0 with no output

- **WHEN** the Drydock plugin cannot be resolved (pure-Codex install, no plugin)
- **THEN** the dispatcher exits 0 with no output (the git pre-commit hook remains the secrets backstop)

### R4 — Agent-agnostic git pre-commit backstop
A git `pre-commit` hook SHALL block committing a staged secret-bearing file, firing for Codex, Claude Code, AND a human `git commit`. It SHALL be self-contained: prefer the plugin's `path_is_secret`, else an inline fallback, so it never fails open on its core job; internal errors (e.g. git unavailable) fail open so a hook bug cannot brick committing.

- **WHEN** a `.env` (or key/credential file) is staged and `pre-commit` runs
- **THEN** it exits non-zero and names the offending file

- **WHEN** only ordinary files (e.g. `README.md`) are staged
- **THEN** `pre-commit` exits 0

### R5 — Installed by init, gated on `.git/` changes
`/drydock:init-project` SHALL copy the `.codex/` bridge into the project and offer to install the git hook, but SHALL require Owner approval before writing under `.git/hooks/` and SHALL never overwrite an existing `pre-commit` (offer to chain/merge instead).

- **WHEN** init runs in a project
- **THEN** the `.codex/` bridge is copied, and the git-hook install is offered with an explicit Owner-approval gate on `.git/hooks/`
