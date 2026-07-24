# Brief

## Change

codex-coplan

## User Need

The Owner's synergy vision: Fable (pilot) and GPT-5.6 (equal ally) work like two devs in a room. The first and most novel piece is the planning conversation — the pilot drafts a plan, the two brains argue it until they're happy, and the output is an agreed plan plus a delegation map (who owns each task, on what model tier). Today the Codex bridge is fire-once (ask, answer, done); there is no back-and-forth negotiation.

## Problem

There is no way to get Codex's honest push-back on a *plan* before building. `codex-review` reviews finished code; mutation writes code. Neither critiques an approach, and neither produces the task decomposition + model-tier assignment the synergy engine needs to route work (flagship only where it earns it; volume to Codex's separate fuel tank and to cheap models). And an unbounded "argue until agreement" loop would burn scarce flagship tokens.

## Problem context

North star from the design conversation: never run out of the Claude 5h window, don't leave usage on the table, keep a ~3h coding floor. Flagship intelligence coordinates (plan, negotiate, decompose, review); cheap subagents execute. Co-planning is where the two brains coordinate — so it is flagship-worthy, but it must be bounded.

## Scope

In scope:

- `negotiate.py` — one read-only critique round: send the plan to Codex as a peer, return a schema-locked critique (`overall`, `converged`, `blocking_concerns`, `gaps`, `risks`, `decomposition` with per-task owner + tier). Secret-guarded, fenced, empty-plan-refused.
- `loop_should_continue` — a pure bounded-loop control: stop on genuine convergence or a round cap (default 2); distrust a `converged` flag that still carries blocking concerns.
- `/drydock:coplan` — the pilot-orchestrated flow: draft → critique → audit (never rubber-stamp) → revise → repeat to the cap → agreed plan + delegation map.

Out of scope (later synergy slices):

- The actual **parallel execution** of the delegation map (throughput fan-out), `mutate --continue`, and the fuel governor — separate pieces.
- Auto-applying Codex's decomposition — the pilot audits and decides; the map is a recommendation.
- The pilot running as Fable specifically — the mechanism is model-agnostic; which flagship pilots is the Owner's session choice.

## Acceptance Criteria

- [ ] A real plan yields a structured critique routed by fuel; Codex's push-back is returned for the pilot to audit.
- [ ] An empty or secret-bearing plan is refused before Codex is spawned.
- [ ] The plan cannot close its own boundary fence.
- [ ] The loop stops on genuine convergence and always stops at the cap; a `converged`-with-blockers contradiction is not trusted.
- [ ] `/drydock:coplan` documents the audit-not-rubber-stamp discipline and the cap.

## Impact Areas

- Backend: `scripts/conductor/negotiate.py` (+ schema).
- Frontend: none.
- Data model: none.
- API: `critique_plan`, `loop_should_continue`, the `negotiate.py` CLI.
- AI/model behavior: a new read-only Codex delegation (plan critique); reuses the verified bridge primitives.
- Documentation: `commands/coplan.md`; operator-guide command count.
- Operations/security: read-only, secret-guarded, fenced — same posture as `codex-review`.

## Open Questions

- Round cap default is 2 (from the design conversation: "one round of push-back, then the pilot decides"). Tunable via `--cap`.
