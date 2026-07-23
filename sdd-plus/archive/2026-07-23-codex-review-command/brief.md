# Brief

## Change

codex-review-command — make the read-only conductor usable in-session: a `/drydock:codex-review` command that delegates a code review to Codex and hands the structured findings back for Claude to audit.

Intake: Mode **STANDARD** (bounded feature over the already-verified read-only conductor; no new security surface). Primary skill: `backend`. Approvals: Owner directed ("make it usable in-session"). Stop conditions: any path that mutates the repo; any secret egress; any non-JSON (traceback) CLI outcome.

## User Need

The conductor (`scripts/conductor/codex_bridge.py`) is proven and archived, but there is no in-session way to invoke it — it's a library, not a feature. The Owner wants to say "have Codex review this" and get a Codex review that Claude then independently audits.

## Problem

No CLI entry point and no command wire the conductor into a session. Without them the two-agent review loop can't be reached by an Owner.

## Scope

In scope:
- `scripts/conductor/review.py` — CLI: discover → gauge → route → guard → bounded reads → delegate a schema-locked review; prints structured JSON for every outcome.
- `scripts/conductor/review_schema.json` — the strict review output schema.
- `commands/codex-review.md` — the `/drydock:codex-review` command: run the CLI, audit findings (confirm/refute/refine, add context), present to the Owner with the fuel footnote.
- Tests `tests/test_codex_review.py` (fake Codex, no quota).
- Delta spec extending `codex-conductor`; operator-guide command count.

Out of scope: mutating review-and-fix; diff/PR ingestion; parallel multi-file fan-out.

## Acceptance Criteria

- [ ] `review.py` returns structured JSON for every outcome (ok, discover, secret_guard, missing_file, too_large, read_error, delegate failure) — never a bare traceback.
- [ ] Read-only + secret-guarded (given paths AND realpaths); content is framed as untrusted data; per-file and total size caps enforced.
- [ ] The command audits Codex's findings rather than rubber-stamping, and never sends secrets.
- [ ] Tests pass with zero Codex quota (fake); full suite green.

## Impact Areas

- Backend: new CLI over the existing conductor.
- API: internal `review()` contract + a new `/drydock:codex-review` command.
- AI/model behavior: adds an in-session two-agent review loop (read-only).
- Documentation: operator-guide command count + the command doc.
- Operations/security: no new surface — reuses the verified read-only + secret-guard; hardened against prompt-injection, oversized input, and read errors (found live by Codex reviewing this very CLI).

## Open Questions

- None blocking. Diff/PR ingestion and multi-file fan-out are deferred.
