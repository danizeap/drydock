# Plan

## Change

endurance-handoff

## Approach

1. `scripts/conductor/handoff.py`:
   - `gather_state()` — deterministic, read-only: branch + HEAD (`git`), active packets (`sdd-plus/changes/*`), open `codex/` worktrees (`git worktree list --porcelain`, filtered), and `executors.fleet_status()`.
   - `fleet_recommendation(fleet)` — advisory: list each usable tank's fuel/reset, flag `<15%` LOW, prefer spending the tank closest to its reset, and always note Claude as human-tracked.
   - `render` → fixed-shape markdown; `write_handoff(next, notes, path, stamp)` writes `HANDOFF.md`; `read_handoff(path)` returns it or None. CLI: `state` / `write` / `read`.
   - Git output decoded UTF-8 (`errors="replace"`) to avoid Windows-locale mojibake.
2. `commands/handoff.md` — the ritual: write on the way out (state → decide next step → write), read on the way in (reconstruct from reality, handle worktrees, then act).
3. Tests: temp git repos (real worktree add for detection) + monkeypatched `fleet_status`; render/write/read; recommendation matrix (near-reset preference, LOW flag, Claude-solo). Operator-guide 11→12. Delta spec.

## Files Expected To Change

- NEW `scripts/conductor/handoff.py`, `tests/test_handoff.py`, `commands/handoff.md`
- `docs/AI_OPERATOR_GUIDE.md` (command count 11→12)
- NEW delta `sdd-plus/changes/endurance-handoff/specs/codex-conductor.md`

## Risks

- **Handoff trusted over reality** — mitigated by the command's explicit reconstruct-from-reality rule (live repo overrides the note); the file records state, never authorizes actions.
- **State-gather failure** — `_git` returns a benign empty result on failure (branch → `(unknown)`), never a traceback.

## Rollback

All new files + one doc-count edit. `git revert` clean; inert unless invoked. No change to `executors`, `codex_bridge`, `mutate`, `review`, or the guards.
