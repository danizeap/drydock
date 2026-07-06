# Brief

## Change

autopilot-floor

## User Need

Drydock's product goal is engineer-level rigor that a non-expert can trust without operating it — a protocol that governs itself. Today the agent starts every session *blind* to project state (it must be told to run `/drydock:status`), the deterministic guardrails can be silently inert with no signal (the v0.1.4→0.1.5 python3-stub bug proved this), and `--force` waives every gate with zero audit trail. This is the additive floor of autonomy: the session orients itself, the guardrails prove they are alive, and overrides leave a paper trail — so the human can just build.

## Problem

1. **No self-orientation.** Nothing surfaces project state at session start. The agent (and Owner) begin unaware of active packets, pending tasks, unfilled verification, or a missing `PROJECT_CONTEXT.md`. This session repeatedly acted on stale git/project state for exactly this reason.
2. **Guardrails can be silently inert.** A hook that fails to run (wrong interpreter, exit != 2) fails open with no signal — the worst failure mode for a safety tool, and one this project already shipped.
3. **Ungoverned overrides.** `sdd.py --force` bypasses the verify/sync/placeholder gates silently and leaves no record of what was waived or why.

## Scope

In scope (v0.2.0 "autopilot floor"):

- `hooks/session_orient.py` (new) — a `SessionStart` hook that does a **read-only** scan of the cwd project and emits `hookSpecificOutput.additionalContext`. It is **silent (empty output, exit 0) outside a Drydock project**, and it **always exits 0** — it can only ever add context, never fail or block a session.
- **Guardrail liveness self-test** inside that hook — pipe a canned `git reset --hard` payload through `git_safety.py` and a `.env` write through `protect_secrets.py`, expecting exit 2 from each; report an honest verdict (only claiming what it tests: the guard scripts are present and block when invoked).
- `hooks/hooks.json` — add the `SessionStart` entry (matchers `startup`, `resume`), `python3 || python` invocation like the others.
- `scripts/sdd.py` (+ scaffold copy) — **governed `--force`**: `--force` requires `--reason "<text>"`; the override is appended as a timestamped record to the change's `decision-log.md`; bare `--force` is refused with a helpful message.

Out of scope (later slices, explicitly not built here):

- `Stop`-hook completion gate (v0.2.1); `PreToolUse` packet-enforcement (v0.2.2).
- User-facing `OWNER_STATUS.md` dashboard and plain-language approval templates (v0.3).
- Auto-classification of LITE/STANDARD/FULL; migrating the exit-2 hooks to the `permissionDecision` JSON API; the SDD+ MCP server.

## Acceptance Criteria

- [ ] In a temp non-Drydock directory, `session_orient.py` emits **nothing** and exits 0.
- [ ] In a Drydock project, it emits `additionalContext` reflecting real state (missing/template/real context; active packets; pending tasks; unfilled verification).
- [ ] An induced internal exception still yields **exit 0** (never blocks a session) — proven by test.
- [ ] The liveness self-test reports **"degraded"** when pointed at a deliberately-broken guard, and **"live"** only when both guards actually block — it can never report live for an inert guard.
- [ ] `sdd.py --force` without `--reason` is refused; with `--reason` it succeeds and appends an override record to `decision-log.md`.
- [ ] pytest green (existing 126 + new), check_sync green (sdd.py pair synced), CI updated; independent verifier review with an adversarial check on the false-"live" property.

## Impact Areas

- Backend: new `hooks/session_orient.py`; `sdd.py` `--force` governance.
- Frontend: none.
- Data model: none (transient `additionalContext`; an append-only override record in `decision-log.md`).
- API: hook I/O contract (stdin SessionStart JSON → stdout additionalContext envelope, always exit 0); `sdd.py` gains `--reason`.
- AI/model behavior: the agent receives project state + guardrail verdict at session start (orientation only; no autonomy is *taken*, only awareness is *given*).
- Documentation: operator guide (new hook + governed force), DEVELOPING.md, CHANGELOG.
- Operations/security: strengthens the enforcement layer's observability; the self-test must never emit a false "live" (release gate).

## Open Questions

- Show the one-line guardrail-liveness verdict in **non-Drydock** sessions too (globally relevant, plugin guards everywhere) or stay fully silent there? Leaning silent-outside-Drydock to minimize surprise; revisit with dogfood feedback. Non-blocking.
