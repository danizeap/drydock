# Plan

## Change

honest-finish

## Approach

1. **New pure helpers in `sdd.py`:**
   - `delta_heading_issues(delta_file)` — level-3 headings under `## ADDED Requirements` that aren't the canonical `### Requirement:` form (`#### Scenario:` and out-of-section headings are not flagged).
   - `packet_unfilled(change_dir)` — required files with placeholder residue or a pending Result (the unified done-predicate's file half).
   - `archive_readiness(change_dir, caps_dir)` — the single read-only blocker list: unattributable delta / unsynced capability / missing requirement / incomplete (pending tasks or unfilled). Returns `[(category, message)]`.
2. **`cmd_verify(name, show_ready_prompt=True)`** — reuse `packet_unfilled`; always lint delta grammar and warn; when green and `show_ready_prompt`, consult `archive_readiness` + `delta_heading_issues` and print exactly one of: a grammar/needs-sync line (never READY on unverifiable grammar), a `/drydock:sync` line (canonical but unsynced), a non-sync blocker line, or `READY TO ARCHIVE`.
3. **`cmd_archive`** — call `cmd_verify(name, show_ready_prompt=False)` for status + the hard missing-artifact exit, then enforce `archive_readiness` (behavior-preserving: block without `--force`, waive+record with it). No living-spec write.
4. **Docs** — `commands/verify.md` step 1 describes the ready line and its fail-toward-sync guarantee.
5. **Scaffold twin** — `scripts/sdd.py` copied to `assets/project-scaffold/scripts/sdd.py`; `check_sync.py` green.

## Files Expected To Change

- `scripts/sdd.py` + its scaffold twin `assets/project-scaffold/scripts/sdd.py`
- `commands/verify.md`
- NEW `tests/test_honest_finish.py`
- NEW delta `sdd-plus/changes/honest-finish/specs/change-packet-gates.md`

## Risks

- **The ready prompt could claim READY falsely** — the whole point. Mitigated by fail-toward-needs-sync: READY requires positive confirmation (synced + canonical), never an empty blocker list, and a regression test asserts a non-canonical unsynced delta never reads READY.
- **Refactoring `cmd_archive` could change gate behavior** — mitigated by keeping the existing gate tests green and adding a block-then-force-waive integration test; the shared helper reproduces the same four gates.
- **The grammar lint could be noisy** — it fires only on genuine level-3 non-canonical headings under ADDED; canonical deltas and scenarios are silent (tested).
- **No living-spec write** — the risky auto-sync is explicitly out of this packet, so nothing here can corrupt the source of truth.

## Rollback

Additive plus one behavior-preserving refactor. `git revert` clean; reverting restores the inline `cmd_archive` gates and drops the prompt/lint. No data migration, no persisted state.
