# Brief

## Change

completion-integrity

## User Need

The v0.2.0 autopilot floor made sessions self-orienting; the next brick of "a protocol that governs itself" is that **"done" must mean verified done**. Today an agent can implement changes against a packet, tell the Owner "finished", and stop — with `verification.md` still `Pending.` — and nothing in the deterministic tier pushes back until archive time (which a novice may never reach). The principle "the implementer's report is evidence, not verification" exists only as prose mid-session.

## Problem

1. **No completion gate in the loop.** The verify step is invoked by habit (agent discipline, tier 1) or at archive (tier 4, end-of-line). Between those, a session can end with unverified claimed-done work and no signal.
2. **The platform makes this subtle.** Confirmed from the docs: a Stop hook's choice is binary — stay silent (stop proceeds) or speak (`decision:"block"` / `additionalContext` — both continue the conversation). There is no inject-and-still-stop, and **no documented loop-prevention flag**: anti-nagging is entirely the hook author's responsibility. A naive implementation nags forever or traps the session.
3. **Nag risk is an adoption risk.** A gate that interrupts pure-conversation sessions, fires twice, or can never be satisfied would erode trust exactly the way blanket `--force` did (the audit's erosion dynamic).

## Scope

In scope (v0.2.1):

- `hooks/completion_gate.py` (new, Stop hook): when — and only when — an active packet whose `verification.md` is still `Pending.` **changed during this session**, block the stop **once per session** with a precise reason (run `/drydock:verify <name>`, or explicitly tell the Owner why verification is deferred). Silent in every other case; always exits 0; fail direction is silent-allow (the archive gates remain the deterministic backstop).
- `hooks/session_orient.py` (MODIFIED): stamps a small session-state file (sanitized session id, start time, packet fingerprints) into the OS temp dir at SessionStart, so the Stop hook can detect "work happened this session" deterministically. Orientation behavior otherwise unchanged; the project tree stays read-only.
- `hooks/hooks.json`: Stop entry (`python3 || python`).
- Tests (nudge-once, loop-safety, false-nudge, silence, state-file attacks), CI smoke, operator guide + CHANGELOG.
- Red-team of the design before implementation; defenses folded into the delta-spec scenarios.

Out of scope (later slices):

- PreToolUse packet enforcement (work with NO packet at all is invisible to this gate — that is v0.2.2's job; stated as a known non-goal here).
- Judging verification *quality* (a filled-but-garbage verification.md passes; the verifier subagent owns semantics).
- The Owner-facing status surface (v0.3).

## Acceptance Criteria

- [ ] A session where a Pending-verification packet's files changed → exactly ONE stop-block with the verify guidance; the next stop proceeds silently.
- [ ] Pure-conversation session (no packet file changes) → never interrupted.
- [ ] No Drydock project / no packets / no state file (orient didn't run) → silent, exit 0.
- [ ] State-file failure modes (missing, corrupt, unwritable, tampered, oversized) → silent-allow, never a loop, never a crash; session_id is sanitized against path traversal.
- [ ] All red-team high/medium findings defended in code and pinned by tests.
- [ ] pytest green, check_sync green; adversarial verifier review (mandate: cannot loop, cannot false-nudge).

## Impact Areas

- Backend: new Stop hook + a bounded state-stamp addition to session_orient.
- Frontend: none.
- Data model: a transient per-session temp file `{session_id, started_at, fingerprints, nudged}`; no project-tree writes.
- API: hooks.json gains a Stop entry; state-file schema is internal to the two hooks.
- AI/model behavior: at most one mid-session course-correction per session; wording routes to `/drydock:verify` or an explicit deferral to the Owner (never demands verification the Owner declined).
- Documentation: operator guide (4-hook inventory, gate semantics), CHANGELOG 0.2.1.
- Operations/security: new writable surface (temp state file) — red-teamed; fail-open by design toward silence.

## Open Questions

- None blocking; design calls logged in decision-log.md. The red-team may add defenses before implementation.
