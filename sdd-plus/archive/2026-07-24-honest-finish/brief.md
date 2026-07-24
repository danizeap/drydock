# Brief

## Change

honest-finish

## User Need

Field report #2's top-weighted finding: Drydock has a strong START and a weak FINISH. `new` is cheap; `archive` is a gated chain that feels marginal-zero at day's end, so it gets skipped. On the reporter's repo: 48 packets, ~0 archived, delta specs never synced. Skipping archive silently rots orientation, the living specs, and handoff. This is the first slice (0.12.0) of the flatten-the-finish work: make the finish *honest and well-timed*. The backlog-drain tooling and the reach-everyone Stop nudge follow in 0.12.1.

## Problem

Two things, one of them a real pre-existing bug:

1. **Nothing tells the operator "you're done, finish it" at the moment they're done.** The friction to archive is partly that the decision happens later (never), not at the instant of green. There is no well-timed prompt.
2. **A vacuous-pass hole lets an unsynced delta read as ready / archive clean.** The archive gate checks "is every delta requirement present in the living spec?" via `delta_added_requirements`, which only recognizes the canonical `### Requirement: <name>` grammar. Deltas authored as `### R5 — <name>` (the habit across recent packets) return `[]` — so the check passes *vacuously* and an unsynced delta archives clean. A Python sync script has been converting the grammar out-of-band, which hid it.

## Scope

In scope:

- One pure `archive_readiness(change_dir, caps_dir)` that both `verify`'s prompt and `archive`'s gate consult, so the prompt can never claim READY on a structural blocker the archive gate would enforce. (On delta *grammar* the prompt is deliberately STRICTER than the archive gate — verify refuses READY on non-canonical grammar; archive warns but still proceeds. Closing that asymmetry is a soft-REJECT / Owner decision, deferred.)
- A ready-at-green prompt in `verify` that **fails toward "needs sync"** — READY only on positive confirmation of synced + canonical deltas, never from an empty blocker list.
- A delta-grammar lint at verify time that warns on non-canonical requirement headings.
- Behavior-preserving refactor of `archive`'s four inline gates onto the shared helper.

Out of scope (deferred, stated):

- **Any write into a living capability spec** — auto-sync is the highest-risk piece and is quarantined to a later packet behind a property test (per the design panel's Packet A / Packet B split).
- The backlog **triage** and `archive --abandon` disposition → 0.12.1.
- The Stop-time archive-ready **nudge** (catches the never-runs-verify operator) → 0.12.1, after `archive_readiness` is extracted into the shared hook module so it isn't duplicated.
- Hard-rejecting non-canonical grammar (WARN only here; REJECT is an Owner decision).

## Acceptance Criteria

- [ ] `verify` on a green + synced + canonical packet prints `READY TO ARCHIVE` with the command.
- [ ] `verify` on a non-canonical delta warns and does NOT print READY (the hole is closed).
- [ ] `verify` on a canonical-but-unsynced delta routes to `/drydock:sync`, not READY.
- [ ] `archive` enforces the same readiness list; `--force` still waives and records the real blockers.
- [ ] Existing gate behavior and tests are preserved; no write touches a living spec.

## Impact Areas

- Backend: `scripts/sdd.py` — the lifecycle CLI.
- Frontend: none.
- Data model: none.
- API: `cmd_verify(name, show_ready_prompt=True)`; new `archive_readiness`, `delta_heading_issues`, `packet_unfilled`; `cmd_archive` refactored onto them.
- AI/model behavior: none.
- Documentation: `commands/verify.md`.
- Operations/security: core lifecycle gates — FULL rigor; read-only, no spec writes.

## Open Questions

- WARN vs REJECT on non-canonical grammar — WARN here (non-breaking, preserves the field habit); REJECT deferred to the Owner and raises the future auto-sync fire-rate.
