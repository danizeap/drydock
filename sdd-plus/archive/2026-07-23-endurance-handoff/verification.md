# Verification

## Change

endurance-handoff

## Automated Checks

- [x] `python -m pytest tests/test_handoff.py -q` → 6 passed (temp git repos + monkeypatched fleet, zero quota): recommendation prefers the near-reset tank, flags a LOW tank, notes Claude-solo; gather→render→write→read round-trip with a real active packet + fleet fuel; missing-file read → None; real `codex/` worktree detected.
- [x] `python -m pytest -q` (full suite) → 337 passed, 3 skipped — no regressions.
- [x] `python scripts/check_sync.py` → 11 pairs identical (plugin-level module, no scaffold twin).
- [x] Live: `handoff.py state` gathered branch/packets/worktrees/fleet; `handoff.py write` rendered a real `HANDOFF.md` (where-we-are, fleet fuel with the near-reset recommendation, next step, notes).

## Manual Checks

- [x] Read-only guarantee: `gather_state()` only reads (git + fs + fleet); the only write is `HANDOFF.md`. The command instructs the incoming leader to reconstruct from live reality — HANDOFF.md is explicitly non-authoritative over `git`/`sdd.py status` (reuses the Resume-playbook rule). Claude's own fuel is human-tracked, honestly (not machine-readable).

## Documentation Updates

- [x] README/operator-guide: `docs/AI_OPERATOR_GUIDE.md` command count 11→12 (`/drydock:handoff`).
- [x] Specs: delta `specs/codex-conductor.md` (R17–R19), to be synced into the living capability.
- [ ] No documentation update needed. Reason:

## Result

VERIFIED. The endurance substrate is in place: a deterministic, read-only HANDOFF.md relay for leadership transfer (re-verified from reality on the way in) plus fuel-aware fleet advice that spends the near-reset tank and human-tracks Claude. Zero quota in CI. This completes the "everything else" build — the remaining vision step (activating Kimi) waits on the Owner installing it. Ready for `/drydock:sync` then archive.
