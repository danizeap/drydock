# Verification

## Change

codex-coplan

## Automated Checks

- [x] `pytest tests/test_negotiate.py -q` — **13 passed**.
- [x] `pytest` (full suite) — **501 passed, 6 skipped**.
- [x] `python scripts/check_sync.py` — OK, 11/11. **Not coverage of this change**: the guarded pairs are root↔scaffold copies and none live under `scripts/conductor/` (negotiate.py is plugin-only, never scaffolded).
- [x] `pytest tests/test_skill_command_registry.py` — 4 passed; the new `coplan` command collides with no skill id.

## Manual Checks

- [x] **Dogfooded live, twice.** First on a throwaway `/health` endpoint plan: Codex gave real senior push-back — caught that returning `db:"down"` with HTTP 200 misleads load balancers, corrected "Supabase `select 1`" (PostgREST doesn't expose arbitrary SQL), flagged the dependency-backed liveness probe as an outage amplifier, and decomposed the work into 5 tasks **all on workhorse/cheap** ("no flagship reasoning needed") — exactly the token-thrift the design targets. Second on `docs/CODEX_PORT_PROPOSAL.md`, where it returned 5 blocking concerns with documentation citations and corrected a factual error in our own architecture proposal.
- [x] **The live run caught a bug the fake could not.** The fake Codex ignores schemas; the real one rejected the first schema with a 400 — OpenAI structured output requires every property of an `additionalProperties:false` object to appear in `required`, and `decomposition.items.why` was optional. Fixed, and the fix also forces Codex to justify each owner/tier assignment.
- [x] The verifier independently confirmed read-only operation (no write path), secret-refusal-before-spawn, fence escalation, schema `required` completeness by inspection, and the bounded-loop ceiling.

## Requirement -> Test Mapping

| Requirement | Test |
| --- | --- |
| Read-only peer critique, fuel-routed | `test_critique_round_runs_the_delegation`, `test_light_round_routes_workhorse` |
| Empty / secret-bearing plan refused before spawn | `test_empty_plan_refused`, `test_secret_bearing_plan_refused_before_sending` |
| No Codex core | `test_no_core` |
| Plan framed as data; round/cap stated; final round decides | `test_prompt_frames_plan_as_data_and_names_the_round`, `test_prompt_forces_a_decision_on_the_final_round` |
| Plan cannot close its own fence | `test_prompt_fence_escalates_if_the_plan_carries_the_marker` |
| Loop stops on genuine convergence | `test_loop_stops_when_both_agree` |
| Loop continues on blocking concerns | `test_loop_continues_on_blocking_concerns` |
| Cap is an absolute ceiling | `test_loop_always_stops_at_the_cap` |
| Contradictory `converged` not trusted | `test_loop_distrusts_converged_true_with_blocking_concerns` |
| Missing/garbage critique degrades safely | `test_loop_handles_a_missing_critique` |

## Documentation Updates

- [x] `commands/coplan.md` — the pilot flow (draft → critique → audit → revise → repeat to cap → agreed plan + delegation map), with the audit-not-rubber-stamp discipline stated.
- [x] `docs/AI_OPERATOR_GUIDE.md` — command count 12 → 13 plus a co-planning line.
- [x] Delta spec `codex-conductor.md` — the two ADDED requirements, synced into the living spec.
- [ ] Project context — no change; extends an existing capability.

## Result

**VERIFIED WITH NOTES — no finding required a code change.** The `verifier` ran against a frozen tree (md5 identical start and end) and reproduced every claimed number exactly: 13 / 501+6 / 11-11 / 4. Both requirements and all seven scenarios are implemented with regression tests, and — notably for the first time in this series — **no requirement was stub-satisfiable**: the loop tests pin the safety property in three opposing directions (always-continue, always-stop, and trust-the-flag each fail a different test), so no stub can pass them all.

Adversarial repros confirmed: read-only with no repo write path (the delegation argv carries the hardcoded `-s read-only --ephemeral` flags); the secret guard fires before discovery/spawn for `sk-`, `sk-proj-`, PEM, AKIA and `ghp_` shapes with zero processes spawned; a plan carrying both `DRYDOCK_FILE_BOUNDARY` and `..._1` escalates the marker to `..._2`; and an invariant sweep over critiques × rounds × caps produced **zero** ceiling violations and no crashes — the cap is absolute even against malformed input.

**Notes accepted, none blocking:** `critique_plan` marks `ok` on `isinstance(result, dict)` without re-validating the critique against the schema (matching `review.py`'s posture — in production Codex's strict structured output guarantees conformance, and schema completeness was confirmed by inspection plus two live runs); a malformed critique below the cap degrades to "continue", always bounded by the cap; and the CLI does not reject `--round > --cap` (cosmetic — the cap still stops it).

**Scope note:** this ships step 3 of the synergy engine (the negotiation). The delegation map it produces is a *recommendation the pilot audits* — automatic fan-out execution, `mutate --continue`, and the pace governor are later slices.
