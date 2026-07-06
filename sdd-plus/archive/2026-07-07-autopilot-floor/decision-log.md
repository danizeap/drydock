# Decision Log

## Change

autopilot-floor

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-06 | Orient via a `SessionStart` hook emitting `additionalContext` | Docs-confirmed channel that injects into the model's context before the first prompt, ships with the plugin (zero user setup) — the deterministic-tier home for orientation. | `UserPromptSubmit` every turn (rejected: repeats context each turn, noisy); a `/drydock:status` habit (rejected: that is the manual burden we are removing). |
| 2026-07-06 | The hook is read-only and **always exits 0** (total try/except) | A SessionStart hook that could fail or hang would break the user's ability to start a session — catastrophic for adoption. It must only ever *add awareness*, never gate. | Let it exit non-zero on error (rejected: risks blocking sessions); block on bad state (rejected: v0.2.0 gives awareness, not enforcement — enforcement is later slices). |
| 2026-07-06 | Silent no-op (empty output, exit 0) outside a Drydock project | Plugin hooks fire in every project; injecting SDD+ status into unrelated work is surprise/noise. Opt-in is "this repo has `sdd-plus/`". | Always emit something (rejected: pollutes every session everywhere); a config flag (rejected: setup burden contradicts the autonomy goal). |
| 2026-07-06 | Liveness self-test invokes the guards as **subprocesses**, "live" only on exit exactly 2 | The failure mode that bit us (python3 stub → hook silently inert) only reproduces through the real wired invocation path; an in-process function call would report "live" while the wired path is dead. | In-process function call (rejected: does not test the path that actually broke); trusting the guards without a check (rejected: silent-inert is the exact class this feature exists to catch). |
| 2026-07-06 | Self-test claims only what it tests, and never blocks | It verifies "the guard scripts are present and block when invoked" — not that hooks.json matchers are wired (that is dev-time tests + check_sync). Overclaiming safety is itself a safety risk. | Claim full protection (rejected: false assurance); skip on any doubt (rejected: the honest partial signal is still the one that catches the real bug). |
| 2026-07-06 | Governed `--force` requires `--reason`, recorded in the change's `decision-log.md` | Overrides must leave an audit trail that travels with the packet into `archive/`; bare `--force` is a silent single-blunt hatch the audit flagged. | Bare `--force` unchanged (rejected: no accountability); a separate top-level overrides ledger (deferred to the v0.3 Owner surface); split `--force-tasks`/`--force-sync` (deferred refinement). |
| 2026-07-06 | Red-team the hook design before implementation | The false-"live" and never-block properties are the release-gating risks; independent adversaries hunting them before code exists is cheaper than finding a hole after. | Rely on the blueprint's risk section alone (rejected: this is exactly where an independent perspective earns its cost); skip and lean on the verifier only (kept as the gate, but pre-implementation red-team hardens the design earlier). |
