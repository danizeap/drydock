---
description: Co-plan with Codex (5.6) as an equal peer before building — negotiate the plan, then get a delegation map
---
Two-brain planning: you (the pilot) draft an implementation plan, then negotiate it with Codex as an EQUAL before any code is written. Codex's critique is **input to your judgment, never authoritative** — you audit it exactly like `/drydock:codex-review`. Read-only; nothing here touches the repo.

Argument: the plan to negotiate — a path to a plan file, or the change name whose `plan.md` to use.

1. **Draft the plan first** (your normal planning — brief/plan, or a scratch plan). It must be real prose, not a stub.
2. **Round 1 — get Codex's push-back.** `python "${CLAUDE_PLUGIN_ROOT}/scripts/conductor/negotiate.py" --file <plan> --round 1 --cap 2`. It discovers the Codex core, routes a model by fuel, and returns JSON `{ok, gauge, route, round, cap, critique, loop}`. The `critique` has: `overall`, `converged`, `blocking_concerns[]`, `gaps[]`, `risks[]`, and a `decomposition[]` (each task with a suggested `owner` = claude/codex/either and `tier` = flagship/workhorse/cheap).
3. **Audit the critique — do not rubber-stamp.** For each blocking concern and gap, decide CONFIRM (fold it into the plan), REFUTE (say why Codex is wrong — it saw only the plan text, not the whole repo), or REFINE. This mutual audit is the point: two frontier models make the plan stronger than either alone.
4. **Revise the plan** to incorporate what you confirmed, then check `loop`:
   - `loop.continue == false` (Codex converged, or the cap was hit) → stop negotiating. Go to step 5.
   - `loop.continue == true` and you have not hit `--cap` → run **round 2** (`--round 2`) on the revised plan. The final round tells Codex to resolve to a decision, so it terminates. The cap is the hard stop — two brains never argue forever.
5. **Produce the agreed plan + the delegation map.** Present: the settled plan, and the per-task delegation (owner + model tier) drawn from `decomposition` and your own judgment. Flagship only where it earns it; push volume to Codex (a separate fuel tank) and to cheap models. Footnote Codex's remaining fuel from `gauge.remaining_percent`.

Non-ok stages, handled plainly (no retry loops): `empty_plan` (draft a real plan first) · `secret_content` (the plan text looks secret-bearing — do NOT send it; strip the secret) · `discover` (Codex isn't installed/updated) · `delegate_timeout`/`bad_model` (report the stage).

Rules: Codex is a peer, not an oracle — its critique is input to your audit. This flow is strictly read-only. The delegation map it helps produce feeds execution (`/drydock:codex-review`, mutating delegation), where the real work — and the real gates — happen.
