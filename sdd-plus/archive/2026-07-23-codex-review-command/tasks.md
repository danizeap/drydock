# Tasks

## Change

codex-review-command

## Implementation

- [x] `scripts/conductor/review.py` + `scripts/conductor/review_schema.json` — read-only review CLI over the verified conductor (structured outcomes, secret+realpath guard, byte caps, untrusted-data framing, OSError→structured).
- [x] `commands/codex-review.md` — the `/drydock:codex-review` command (run CLI → audit findings → present with fuel footnote).
- [x] `tests/test_codex_review.py` — fake-Codex, no quota: happy / light-route / secret-refused / no-core / missing / too-large / untrusted-framing.
- [x] Docs — operator-guide command count 10 → 11.
- [x] Delta spec `specs/codex-conductor.md` (ADDED review-command requirement).
- [x] Run verification — review tests 7 passed; full suite 310 passed; check_sync 11/11; live Codex self-review round-trip exercised and its findings audited + resolved.
