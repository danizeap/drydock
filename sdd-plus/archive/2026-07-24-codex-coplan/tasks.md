# Tasks

## Change

codex-coplan

## Implementation

- [x] `negotiate_schema.json` — critique shape (overall/converged/blocking/gaps/risks/decomposition), strict, every property required (strict-mode fix from the live dogfood).
- [x] `negotiate.py` — `_build_prompt` (peer framing, fenced plan, round/cap, final-round decision), `critique_plan` (empty/secret refusal before spawn, discover→gauge→route→delegate, size-scaled timeout), `loop_should_continue` (pure, converge-or-cap, distrusts converged-with-blockers), CLI.
- [x] `commands/coplan.md` — pilot flow: draft → critique → audit (never rubber-stamp) → revise → repeat to cap → agreed plan + delegation map.
- [x] Operator guide — command count 12 → 13; co-planning line.
- [x] `tests/test_negotiate.py` — 13 tests: delegation plumbing (heavy→flagship, light→workhorse), empty/secret refusal, no-core, prompt framing/final-round/fence-escalation, loop stop-on-agree / continue-on-blockers / always-stop-at-cap / distrust-converged-with-blockers / missing-critique.
- [x] **Dogfooded live**: Codex critiqued a real /health-endpoint plan — caught a 200-vs-degraded semantics bug, corrected "Supabase select 1", flagged the liveness-probe outage risk, and decomposed into 5 tasks all on workhorse/cheap. The live run also surfaced (and I fixed) the strict-schema `required` bug the fake couldn't.
- [x] Run verification — negotiate 13 passed; full suite **501 passed, 6 skipped**; check_sync 11/11; registry 4 passed; `verifier` subagent VERIFIED WITH NOTES on a frozen tree, no finding requiring a code change.
