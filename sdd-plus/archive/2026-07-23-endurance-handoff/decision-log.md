# Decision Log

## Change

endurance-handoff

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-23 | State is gathered DETERMINISTICALLY from git + packets + fleet; the leader supplies only the one-line next step + notes | The whole point of the relay is to resume from *reality*, not a lossy recap — so the machine reconstructs the facts and the human/agent adds only judgment | Free-text the whole handoff (rejected: exactly the stale-recap problem the ritual exists to kill) |
| 2026-07-23 | The incoming leader MUST reconstruct from reality; HANDOFF.md never overrides the live repo | Reuses the framework's Resume-playbook rule ("current repository truth overrides any recap text"); a handoff that's trusted blindly re-introduces drift | Treat HANDOFF.md as authoritative (rejected: notes go stale the moment anything changes) |
| 2026-07-23 | No auto-trigger on low fuel in v1 | Claude's own quota is not machine-readable, so "we're low" is Owner-driven or an estimate; auto-triggering on a number we can't read would be theatre | Auto-write a handoff at a fuel threshold (rejected: no reliable Claude fuel signal to trigger on) |
| 2026-07-23 | `fleet_recommendation` prefers spending the tank CLOSEST to its reset | The endurance principle: spend fuel that's about to refill for free; protect the far-reset tank as reserve. Advisory now, load-bearing once ≥2 tanks are usable | Spend the fullest tank (rejected: wastes a soon-to-refill tank and drains the reserve); no advice (rejected: the routing insight is the point) |
| 2026-07-23 | STANDARD mode, no verifier subagent | Read-only state gather + a single-file writer over already-verified code; the risks (mutation, trust-over-reality) are covered by the read-only design + the command rule + tests | FULL mode (rejected: no mutating or security surface) |
