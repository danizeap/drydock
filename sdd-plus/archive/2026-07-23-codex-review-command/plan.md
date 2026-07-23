# Plan

## Change

codex-review-command

## Approach

1. `scripts/conductor/review.py` — `review(paths, weight)` calls the verified `codex_bridge` primitives: `discover_core` → `read_rate_limits`/`summarize_gauge` → `route` → `guard_outbound` (given paths + realpaths) → bounded, error-handled reads → `delegate` with the shipped schema. Returns a structured dict for every outcome; `main()` prints it and exits 0/1. Hardened per a live Codex self-review: content framed as untrusted data (prompt-injection), per-file/total byte caps, `OSError` caught to a `read_error` stage.
2. `scripts/conductor/review_schema.json` — strict `{overall_assessment, findings[]}` schema.
3. `commands/codex-review.md` — run the CLI via `${CLAUDE_PLUGIN_ROOT}`, handle non-ok stages plainly, **audit** findings (confirm/refute/refine + additions), present with a fuel footnote. Codex output is input to the audit, never authoritative.
4. Tests `tests/test_codex_review.py` — monkeypatch `discover_core` to the fake so the whole path runs through the real subprocess layer with no quota; cover happy/light-route/secret/no-core/missing/too-large + the untrusted-data framing.
5. Delta spec extends the `codex-conductor` living capability; bump the operator-guide command count 10 → 11.

## Files Expected To Change

- NEW `scripts/conductor/review.py`, `scripts/conductor/review_schema.json`
- NEW `commands/codex-review.md`
- NEW `tests/test_codex_review.py`
- `docs/AI_OPERATOR_GUIDE.md` (command count)
- NEW delta `sdd-plus/changes/codex-review-command/specs/codex-conductor.md`

## Risks

- **Prompt injection via reviewed content** — mitigated by the untrusted-data framing; residual is inherent to sending code to a model (documented).
- **Symlink-to-secret** — mitigated by guarding realpaths too.
- **Oversized/binary input** — byte caps + `errors="replace"` reads.

## Rollback

All new files + one doc-count edit. `git revert` clean; the command is inert unless invoked. No change to the conductor or the guards.
