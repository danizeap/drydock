# Tasks

## Change

backlog-drain

## Implementation

- [x] `_classify_packet` — precedence buckets (IN-PROGRESS / CLAIMED-DONE-UNVERIFIED / NEEDS-SYNC / ARCHIVE-READY); any error → UNKNOWN, never aborts the batch.
- [x] `cmd_triage` — read-only, per-bucket counts + next action, kebab-only, ordered ready → unknown.
- [x] `_replace_result_section` + `_unsynced_requirements` — swap the Result body; list canonical delta reqs absent from a living spec.
- [x] `cmd_abandon` — honest `Abandoned … never verified` Result, Override recorded, entomb warning, move-only; requires `--reason`; refuses to combine with `--force`.
- [x] CLI wiring: `triage` subcommand, `--abandon` flag, abandon/force mutual-exclusion.
- [x] `commands/archive.md` — triage + abandon documented.
- [x] Scaffold twin `assets/project-scaffold/scripts/sdd.py`; check_sync 11/11.
- [x] `tests/test_backlog_drain.py` — bucket-per-state, non-canonical → needs-sync, missing-file → in-progress-not-crash, triage survives a broken packet, result-section swap/append, unsynced-requirements, abandon records-absence-never-pass, entomb warning, requires-reason, force/abandon exclusive, move-never-delete.
- [x] Dogfooded triage + abandon on a synthetic backlog (buckets correct; abandon wrote the honest Result + Override).
- [x] **Verifier findings 1–4 fixed**: entomb warning now covers non-canonical/unattributable deltas (was silent — the exact hole I flagged); collision check moved before any mutation (atomic); malformed `## Result: PASS` heading scrubbed clean; whitespace-only reason refused. Each with a regression test.
- [x] Run verification — sdd suites 52 passed; full suite (below); check_sync 11/11; `verifier` subagent (VERIFIED WITH NOTES, all four findings addressed).
