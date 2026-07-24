# Plan

## Change

backlog-drain

## Approach

1. **`_classify_packet(change_dir, caps_dir)`** — precedence: missing required files or pending tasks → IN-PROGRESS; else unfilled placeholders / pending Result → CLAIMED-DONE-UNVERIFIED; else non-canonical grammar or non-empty `archive_readiness` → NEEDS-SYNC; else ARCHIVE-READY. Wrapped so any exception → UNKNOWN (never aborts the batch). Reuses the 0.12.0 predicates.
2. **`cmd_triage()`** — read-only; buckets all kebab-named packets, prints per-bucket counts + a next action, ordered ready → unknown.
3. **`_replace_result_section` / `_unsynced_requirements`** — swap the `## Result` body (append if absent); list canonical delta requirements absent from a living spec.
4. **`cmd_abandon(name, reason)`** — write `Abandoned <date> — never verified. Reason: …` into the Result, record an Override (so brief.py demotes, same as a forced archive), warn on entombed unsynced requirements, `shutil.move` to `archive/`. Requires reason; refuses to combine with `--force` (dispatched in `main`).
5. **CLI** — `triage` subcommand; `--abandon` flag on `archive`; abandon/force mutual-exclusion in `main`.
6. **Scaffold twin + docs** — `assets/project-scaffold/scripts/sdd.py`; `commands/archive.md` documents triage + abandon.

## Files Expected To Change

- `scripts/sdd.py` + scaffold twin `assets/project-scaffold/scripts/sdd.py`
- `commands/archive.md`
- NEW `tests/test_backlog_drain.py`
- NEW delta `sdd-plus/changes/backlog-drain/specs/change-packet-gates.md`

## Risks

- **Abandon writes a file and moves a packet** — the most side-effectful path here. Mitigated: Owner-invoked, `--reason` required, only moves (never deletes — tested), records the honest `Abandoned` Result and an Override, and warns before burying unsynced spec knowledge.
- **Triage misclassifies** — advisory only (read-only), so a wrong bucket costs a wrong suggestion, never data. The precedence is explicit and tested per bucket.
- **A broken packet aborting the sweep** — the exact messiest-backlog case; guarded by per-packet try/except → UNKNOWN, tested.
- **Abandon fabricating a pass** — structurally impossible: it writes only the `Abandoned … never verified` string and records an Override; a regression test asserts `PASS` never appears.

## Rollback

Additive — new subcommand, new flag, new functions; nothing existing changed. `git revert` clean. No persisted state, no migration.
