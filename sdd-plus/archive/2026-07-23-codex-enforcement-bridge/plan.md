# Plan

## Change

codex-enforcement-bridge

## Approach

Reuse the plugin's guard logic (single source of truth); the bridge is mostly wiring, because Codex speaks the same `permissionDecision: deny` protocol Drydock already emits (v0.5.0).

1. **Dispatcher** `assets/project-scaffold/.codex/hooks/drydock_guard.py`:
   - Read the Codex PreToolUse tool JSON on stdin.
   - Resolve the installed Drydock plugin's `hooks/` dir (the secpho pattern: `~/.claude/plugins/.../drydock@drydock/.../hooks`), `sys.path`-insert it, import `protect_secrets` and `git_safety`.
   - **Normalize Codex tool names** so the plugin guards apply unchanged: `apply_patch`/`Edit`/`Write` → path-based secret check (`protect_secrets.check`); `Bash`/`PowerShell` → command check (`git_safety.check_command` for destructive git + `protect_secrets.check` for command write targets). Pass `tool_name` through faithfully for the shell tools so the PowerShell path fires.
   - On a deny, emit the JSON `permissionDecision: deny` on stdout and **exit 0**. On ANY error (unresolvable plugin, malformed input, import failure) → **exit 0, no output (fail open)** — a guardrail bug must never brick a Codex session.
2. **`assets/project-scaffold/.codex/hooks.json`**: `PreToolUse` matcher `^(Bash|PowerShell|apply_patch|Edit|Write)$`; `command` = `python .codex/hooks/drydock_guard.py`, `commandWindows` = `py -3 .codex\hooks\drydock_guard.py` (Codex's clean cross-platform mechanism — no `python3 || python`).
3. **Git pre-commit hook** `assets/project-scaffold/hooks/git/pre-commit`: for each staged file, run the shared `path_is_secret`; if a secret-bearing path is staged, print the reason and exit 1 (block the commit). Agent-agnostic — fires for Codex, Claude Code, and a human `git commit`.
4. **`commands/init-project.md`**: install the `.codex/` bridge + the git hook (`git config core.hooksPath` or copy into `.git/hooks/`), and note in AGENTS.md that enforcement is now cross-tool.
5. **Tests** `tests/test_codex_enforcement.py`: replay Codex tool shapes (`apply_patch` `.env`, `Bash` `git reset --hard`, `PowerShell` `Set-Content .env`) through the dispatcher as a subprocess → assert JSON deny + exit 0; benign → silent exit 0; malformed/unresolvable → exit 0 (fail open). Pre-commit hook: staged `.env` → exit 1; staged README → exit 0.

## Files Expected To Change

- `assets/project-scaffold/.codex/hooks/drydock_guard.py` (new), `assets/project-scaffold/.codex/hooks.json` (new)
- `assets/project-scaffold/hooks/git/pre-commit` (new)
- `commands/init-project.md`, `AGENTS.md` (+ scaffold twin) — cross-tool enforcement note
- `tests/test_codex_enforcement.py` (new)
- `docs/AI_OPERATOR_GUIDE.md`, `README.md`, `CHANGELOG.md` (at release)
- Delta spec: a new `codex-enforcement-bridge` capability (the dispatcher contract + fail-open)

## Risks

- **Fail-open when the plugin isn't resolvable** — for pure-Codex users (no Claude plugin) the dispatcher currently can't reach the guards and fails open (unguarded). Mitigation for v1: document it; the git pre-commit hook still catches the secrets class agent-agnostically; a bundled self-contained guard copy is a fast-follow. STOP CONDITION honesty: the brief states this limitation, not hidden.
- **False-block on Codex `apply_patch`** — its payload shape differs from Write; must extract the target path correctly (test it).
- **Tool-name drift** — if Codex renames tools, the matcher/normalization needs updating; pin the current names in a test.

## Rollback

All new files; reverting removes the `.codex/` bridge and git hook. No change to the existing Claude Code hooks. `git revert` clean.
