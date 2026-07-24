# Plan

## Change

codex-coplan

## Approach

1. **`negotiate_schema.json`** — the critique's shape: `overall`, `converged`, `blocking_concerns[]`, `gaps[]`, `risks[]`, `decomposition[]` (task/owner/tier/why). Strict (`additionalProperties:false`), and — the dogfood-found requirement — every property listed in `required` (OpenAI structured output rejects a strict schema otherwise).
2. **`negotiate.py`**, mirroring `review.py`'s verified path:
   - `_build_prompt(plan, round, cap)` — frame the pilot as a peer wanting push-back; fence the plan (reusing `review._fence`) so content can't close it; tell Codex the round/cap and, on the final round, to resolve to a decision.
   - `critique_plan(plan, weight, round, cap)` — refuse empty / secret-bearing (`review.content_has_secret`) before spawning; discover → gauge → route → delegate(schema); size-scaled timeout.
   - `loop_should_continue(critique, round, cap)` — pure; stop on genuine convergence or cap; a `converged`-with-blockers contradiction is distrusted (continue, fail-safe).
   - `main()` — `--file`/stdin, `--round`, `--cap`, `--weight`; JSON out; attaches `loop`.
3. **`commands/coplan.md`** — the pilot flow: draft → critique → audit (confirm/refute/refine, never rubber-stamp) → revise → repeat to cap → agreed plan + delegation map.
4. **Operator guide** — command count 12 → 13; a line on co-planning.

## Files Expected To Change

- NEW `scripts/conductor/negotiate.py`, `scripts/conductor/negotiate_schema.json`
- NEW `tests/test_negotiate.py`
- NEW `commands/coplan.md`
- NEW delta `sdd-plus/changes/codex-coplan/specs/codex-conductor.md`
- `docs/AI_OPERATOR_GUIDE.md`

## Risks

- **Codex's critique treated as authoritative** — it is a peer, not an oracle; the command doc mandates the pilot audit it (confirm/refute/refine), exactly like `codex-review`.
- **Unbounded token burn** — the whole reason for the cap; `loop_should_continue` always stops at `--cap`, tested.
- **A plan carrying a secret** — refused by `content_has_secret` before Codex is spawned, tested.
- **Prompt injection via the plan** — the plan is fenced with an escalating marker it cannot close, tested.
- **New Codex delegation surface** — read-only, reuses the verified `codex_bridge` primitives; no new sandbox or write path.

## Rollback

Purely additive — new files, one operator-guide line. `git revert` clean; nothing depends on `negotiate.py`. The existing conductor paths are untouched.
