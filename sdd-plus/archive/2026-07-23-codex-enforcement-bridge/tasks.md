# Tasks

## Change

codex-enforcement-bridge

## Implementation

- [x] Delta spec `specs/codex-enforcement-bridge.md` (dispatcher deny/allow/fail-open + git backstop + init gate).
- [x] Dispatcher `assets/project-scaffold/.codex/hooks/drydock_guard.py` — resolves the plugin guards, reuses `git_safety`/`protect_secrets`, normalizes Codex tool names, handles `apply_patch` path extraction, emits the JSON deny, fails open on any error.
- [x] `assets/project-scaffold/.codex/hooks.json` — PreToolUse matcher + `command`/`commandWindows`.
- [x] `assets/project-scaffold/hooks/git/pre-commit` — agent-agnostic secrets backstop (plugin matcher with inline fallback).
- [x] Tests `tests/test_codex_enforcement.py` — Codex-shaped payloads → deny/allow/fail-open through the dispatcher; git hook blocks a staged secret, allows a normal file.
- [x] `/drydock:init-project` wiring — copy `.codex/`, offer the git-hook install with an Owner-approval gate on `.git/hooks/`.
- [x] Run verification — `pytest` green, `check_sync` green, then the `verifier` subagent.
