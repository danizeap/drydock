# Decision Log

## Change

coord-shared-gauge

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-23 | Share the gauge + meter concurrency; DO NOT reserve fuel-% | Design panel (5 approaches, adversarially critiqued) converged: the gauge is integer-percent-of-a-weekly-window and per-turn burn is sub-1% / unquantifiable in %, so any "reserved %" is FABRICATED — dishonest, phantom-scarce, and it fails SILENTLY (never raises, so fail-open never fires -> confidently-wrong fleet) | Fuel-% reservation ledger (rejected: the panel's unanimous kill — my own first instinct, corrected by the workflow); budget/fairness (deferred: not honestly computable) |
| 2026-07-23 | Daemon-free, file-based, execution stays session-side | A broker that executes delegations blocks every session if it wedges (violates fail-safe) and orphans fuel-burning Codex children on Windows (no process groups) -> re-delegation -> double-spend on a hard weekly tank | Broker/daemon (rejected: breaks fail-safe, worst on Windows); the current session-side path already collapses failures to "lost a count" |
| 2026-07-23 | FAIL-OPEN is the load-bearing invariant — every path degrades to a direct read | A coordination bug must NEVER brick or block a session; coordination is a pure optimization that can vanish at any instant, reverting to today's proven independent behavior | Any design where correctness depends on the cache/lock succeeding (rejected) |
| 2026-07-23 | State dir off `~/.codex` and off OneDrive (`%LOCALAPPDATA%\Drydock`) | Writing into `~/.codex` is the contention we're removing; a OneDrive-synced dir reintroduces `os.replace` sharing-violation churn | `~/.drydock` (rejected on Windows: risk of Known-Folder-Move/OneDrive sync); inside `~/.codex` (rejected: the exact shared state we avoid) |
| 2026-07-23 | Best-effort single-flight, not mutual exclusion; stale locks are stealable | Perfect mutual exclusion isn't needed — worst case is a couple of redundant reads (== today). A stealable stale lock (> the 25s read timeout) guarantees no deadlock when a holder crashes | A real cross-process mutex (rejected: heavier, deadlock risk on crash, cross-platform pain for a pure optimization) |
| 2026-07-23 | Serve age-adjusted real numbers only; surface `source`+`as_of_age_s` | Honesty ethos: never present a stale number as fresh. Adjusting the reset countdown by cache age keeps it correct without needing to re-read | Serve the frozen cached number (rejected: reset countdown drifts a full TTL, mildly dishonest) |
| 2026-07-23 | Global `conftest` state isolation | Wiring coord into `status()` made fleet-reading tests pollute the machine's REAL cache with test data a live session could read — caught during the live demo | Per-test env setup (rejected: easy to forget on the next test that reads fuel) |
