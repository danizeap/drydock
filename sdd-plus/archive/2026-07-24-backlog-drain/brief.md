# Brief

## Change

backlog-drain

## User Need

Field report #2: 48 packet dirs, ~0 archived, `sdd-plus/changes/` a junk drawer, orientation decayed to noise. 0.12.0 made the finish honest and well-timed *going forward*; this slice (0.12.1) gives the operator the tooling to **drain the existing backlog** — deliberately, without fabricating verifications they never had or abandoning genuinely-shipped work.

## Problem

The 48 packets are abandoned MID-lifecycle, so neither extreme is right: "archive them all" would force clean archives on unverified work (and `--force` would still leave no honest record of *why*); "leave them" keeps the rot. There is no read-only way to see what state each packet is in, and no honest disposition for a packet that was genuinely abandoned (real work, never verified, not worth verifying now) — the only escape hatch, `--force`, is for waiving a gate on work you *stand behind*, which is the opposite intent.

## Scope

In scope:

- `sdd.py triage` — read-only, buckets every active packet (ARCHIVE-READY / NEEDS-SYNC / CLAIMED-DONE-UNVERIFIED / IN-PROGRESS / UNKNOWN) with a per-bucket next action, robust to a broken packet.
- `archive --abandon --reason "<why>"` — an honest disposition distinct from `--force`: records `Abandoned — never verified` (never a PASS), logs an Override, warns when it buries unsynced spec knowledge, only moves (never deletes), requires a reason, mutually exclusive with `--force`.

Out of scope (deferred, stated):

- The Stop-time archive-ready **nudge** (reaching the operator who never runs verify) → still 0.12.x-later, after `archive_readiness` is extracted into the shared hook module.
- **Auto-sync** into a living spec → Packet B, behind a real-corpus property test.
- A dedicated `/drydock:triage` slash command (the `sdd.py triage` subcommand is documented under `/drydock:archive`); a distinct archive location for abandoned packets (Owner decision — they go to `archive/` with the honest Result marker).

## Acceptance Criteria

- [ ] `triage` labels each of verified+synced / canonical-unsynced / tasks-done-verification-pending / tasks-pending correctly and writes nothing.
- [ ] `triage` buckets a broken packet instead of aborting the sweep.
- [ ] `archive --abandon` writes an `Abandoned … never verified` Result (no PASS), logs an Override, moves to `archive/`, and warns when it buries an unsynced requirement.
- [ ] `--abandon` requires `--reason` and refuses to combine with `--force`.
- [ ] Abandon only moves — it never deletes.

## Impact Areas

- Backend: `scripts/sdd.py` (+ scaffold twin).
- Frontend: none.
- Data model: none.
- API: new `triage` subcommand; new `--abandon` flag; `cmd_abandon`, `cmd_triage`, `_classify_packet`, `_replace_result_section`, `_unsynced_requirements`.
- AI/model behavior: none.
- Documentation: `commands/archive.md` (triage + abandon).
- Operations/security: `--abandon` moves a packet and writes its verification Result — Owner-invoked, `--reason` required, records everything, never deletes.

## Open Questions

- Where abandoned packets live (archive/ vs a distinct dir) is left an Owner decision; they currently go to `archive/` distinguished by the `Abandoned` Result marker + the Override record.
