# Brief

## Change

endurance-handoff — the endurance substrate: a `/drydock:handoff` command + `HANDOFF.md` relay so leadership transfers between agents (fresh Claude, Codex, future Kimi) without losing the thread, plus fuel-aware fleet advice.

Intake: Mode STANDARD (read-only state-gathering + a single-file writer over verified code). Primary skill: `backend`. Approvals: Owner directed "build everything else" toward the endurance layer (#3). Stop conditions: any state-gathering that mutates the repo; a handoff treated as authoritative over live repo truth.

## What this means for your product

This is the piece that makes "code all day" literal. When one driver's tank empties, the outgoing leader writes exactly where things stand — branch, open Codex worktrees, active packets, fleet fuel, the one next step — and the incoming leader picks up from reality. Switching drivers stops meaning "re-explain everything."

## User Need

The fleet can now read its tanks (executor-fleet), but nothing lets leadership *transfer*. Without a relay, a handoff means a lossy recap; the whole reset-to-reset endurance goal needs a durable, deterministic "where we are."

## Scope

In scope: `scripts/conductor/handoff.py` — deterministic `gather_state()` (branch, HEAD, active packets, open `codex/` worktrees, `fleet_status()`), `fleet_recommendation()` (advisory: spend the near-reset tank, flag low ones, Claude human-tracked), `render`/`write_handoff`/`read_handoff`, CLI (`state`/`write`/`read`). `commands/handoff.md` (the ritual, incl. reconstruct-from-reality). Tests (temp git repos + monkeypatched fleet, no quota). Operator-guide command count 11→12. Delta spec.

Out of scope: automatic handoff triggers (Claude can't self-read its own quota — the Owner/estimate decides); full multi-tank routing optimization (realizes once ≥2 tanks are usable).

## Acceptance Criteria

- [ ] `gather_state()` is read-only and reports branch, HEAD, active packets, open `codex/` worktrees, and the fleet.
- [ ] `write_handoff` renders a fixed-shape `HANDOFF.md` (where-we-are / fleet fuel / next step / notes); `read_handoff` returns it or None.
- [ ] `fleet_recommendation` prefers spending the near-reset tank, flags a low tank, and notes Claude as human-tracked.
- [ ] The command tells the incoming leader to reconstruct from reality (live repo overrides the note).
- [ ] Tests pass with zero Codex quota (monkeypatched fleet); full suite green.

## Impact Areas

- Backend: new `handoff.py`.
- API: the HANDOFF.md format + `gather_state`/`fleet_recommendation`.
- AI/model behavior: enables leadership transfer across agents (the endurance loop).
- Documentation: `commands/handoff.md`; operator-guide command count.
- Operations/security: read-only gather; handoff never authorizes side effects.

## Open Questions

- Auto-trigger on low fuel: deferred (Claude's own quota isn't machine-readable; Owner-driven for now).
