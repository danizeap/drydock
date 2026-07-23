# Tasks

## Change

endurance-handoff

## Implementation

- [x] `scripts/conductor/handoff.py` — deterministic `gather_state`, `fleet_recommendation`, `render`/`write_handoff`/`read_handoff`, CLI (`state`/`write`/`read`); UTF-8 git decode.
- [x] `commands/handoff.md` — the `/drydock:handoff` ritual (write out / read in with reconstruct-from-reality).
- [x] `tests/test_handoff.py` — recommendation matrix (near-reset preference, LOW flag, Claude-solo), gather/render/write/read, real `codex/` worktree detection (temp repos, monkeypatched fleet, no quota).
- [x] Docs — operator-guide command count 11→12 (`/drydock:handoff`).
- [x] Delta spec `specs/codex-conductor.md` (handoff requirements).
- [x] Run verification — handoff tests 6 passed; full suite green; check_sync 11/11; live `handoff write` rendered a real HANDOFF.md.
