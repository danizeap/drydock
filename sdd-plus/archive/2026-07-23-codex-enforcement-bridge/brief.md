# Brief

## Change

codex-enforcement-bridge (v0.6.0) — the first brick of multi-agent orchestration: make Drydock's deterministic guards enforce on Codex and on any git commit, not only inside Claude Code.

Intake: Mode FULL (deterministic-enforcement tier). Primary skill: backend. Approvals: Owner directed this after the Codex capability audit (2026-07-23, `sdd-plus/specs/multi-agent-orchestration-vision.md` §7) confirmed Codex uses the *same* `permissionDecision: deny` hook protocol. Stop conditions: any fail-open on a real destructive/secret command through the Codex path; any false-block; scope growth into the conductor/usage-routing layer (that is later work, gated on the Claude-side usage-query answer still pending).

## What this means for your product

When you run Codex on a Drydock project — or when *anything* commits, agent or human — the same "can't be talked out of" guards that protect your Claude Code sessions now protect you too. The safety floor stops being Claude-Code-only.

## User Need

Drydock's Tier-4 enforcement (the deny-guards) currently only fires inside Claude Code, via the plugin's `hooks.json`. The moment you add Codex to the same repo — the whole point of the orchestration vision — Codex is **unguarded**: it can write `.env`, run `git reset --hard`, create ungoverned migrations, and nothing stops it. The Codex audit resolved that this is fixable cheaply: Codex reads `.codex/hooks.json` with the identical PreToolUse `permissionDecision: deny` protocol Drydock already emits (the v0.5.0 JSON-deny migration is exactly what makes the guards portable), and normal git pre-commit hooks fire on Codex's commits. So the enforcement can be brought to Codex with near-zero new guard logic — mostly wiring.

## Problem

1. A Drydock project has no `.codex/` enforcement, so Codex bypasses every guard.
2. There is no agent-agnostic backstop: a human `git commit` of a `.env` is also unguarded.
3. Codex users may not have the Claude Code plugin installed, so the guards must be reachable from the *project*, not only the plugin.

## Scope

In scope:

1. **`.codex/hooks/drydock_guard.py`** — a project-side dispatcher that runs the deny-guards and emits the `permissionDecision: deny` protocol. It resolves the guard logic by importing the installed Drydock plugin's `protect_secrets`/`git_safety` (+ `_drydock_common`) — the same resolution the secpho reference uses — and **fails open (exit 0) on any error** (a guardrail bug must never brick a Codex session). It normalizes the Codex tool names (`apply_patch` → treated as an edit/write; `Bash`/`PowerShell` → command) so the plugin guards apply unchanged.
2. **`.codex/hooks.json`** — wires the dispatcher to `PreToolUse` with matcher `^(Bash|PowerShell|apply_patch|Edit|Write)$`, `command` (POSIX) + `commandWindows` (the clean cross-platform answer Codex provides — no `python3 || python` needed).
3. **A git pre-commit hook** (`hooks/git/pre-commit`, installed to the project) — blocks committing a secret-bearing file (agent-agnostic: fires for Codex, Claude Code, and a human). Uses the shared `path_is_secret`.
4. **`/drydock:init-project` wiring** — installs the `.codex/` bridge + the git hook, and notes in AGENTS.md that enforcement is now cross-tool.
5. Tests: replay Codex-shaped payloads (`apply_patch`/`Bash`/`PowerShell` with `.env` and `git reset --hard`) through the dispatcher → JSON deny; benign → silent; malformed/unresolvable → fail-open exit 0. Pre-commit hook blocks a staged secret, allows a normal file.

Out of scope (later bricks, in the vision note):

- The conductor / usage-aware routing / model-selection layer (gated on the pending Claude-side usage-query answer).
- packet_guard on Codex (stateful; the stateless secrets + destructive-git guards are the critical floor for v1).
- True-parallel worktrees and the HANDOFF.md relay ritual.

## Acceptance Criteria

- [ ] A destructive-git and a secret-write payload in Codex tool shapes (`Bash`/`PowerShell`/`apply_patch`) are DENIED via the JSON protocol through `drydock_guard.py`; benign is silent; malformed/unresolvable input fails open (exit 0).
- [ ] The git pre-commit hook blocks a staged `.env`/key and allows a normal file.
- [ ] No new guard *logic* is duplicated — the dispatcher reuses the plugin guards (single source of truth); the false-block traps and the JSON protocol are inherited, not re-derived.
- [ ] Full suite green; verifier confirms no fail-open on a real destructive/secret command and no false-block, adversarially.

## Impact Areas

- Backend: new `hooks/codex/` (or scaffold `.codex/`) dispatcher + git hook; `commands/init-project.md`.
- Operations/security: THIS is the cross-tool enforcement floor — FULL mode.
- Documentation: README + operator guide ("works with Codex" upgraded from *follows rules* to *enforced*).

## Open Questions

- None blocking. Deferred: whether pure-Codex (no plugin) users should get a fully self-contained bundled guard copy vs. the plugin-resolution path — v1 resolves the plugin and fails open if absent; a bundled copy for plugin-less Codex is a fast follow.
