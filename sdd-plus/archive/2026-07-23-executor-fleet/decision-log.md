# Decision Log

## Change

executor-fleet

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-23 | Hardcode exactly two executors (Codex, Kimi) behind a small interface — not a generic third-party plugin loader | Only 2–3 executors are realistically worth supporting; a bounded interface gives the "pick your stack" agency without the over-engineering + attack surface of arbitrary plugins | A generic plugin system (rejected: over-built for 2 adapters, larger risk surface); hardcode Codex only (rejected: Owner wants Kimi staged now) |
| 2026-07-23 | Kimi ships STAGED — `verified=False`, refuses to run, never `usable` — until an on-machine live-fire proof | Everything known about Kimi is web docs; the Codex reality-check proved web assumptions (stale binary, config skew, flagship gate) are wrong. Nothing is treated as working until proven here | Ship a "working" Kimi adapter from docs (rejected: the exact blind-build the discipline forbids); omit Kimi entirely (rejected: Owner wants the slot ready) |
| 2026-07-23 | `available()` (presence) is separate from `verified` (proven); presence never implies usable | A binary installed is not a binary that works with this account/config — the Codex lesson. Present-but-unverified is a distinct `staged` state | Treat "installed" as "ready" (rejected: false readiness is how the Codex integration would have silently failed) |
| 2026-07-23 | Claude (the conductor) is listed separately in `fleet_status`, not as an executor with a fuel read | Claude's own quota is not machine-readable (established); modelling it as a readable tank would be a lie | Fake a Claude fuel number (rejected: dishonest); omit Claude (rejected: the Owner needs the whole picture) |
| 2026-07-23 | Wrap the proven `codex_bridge` rather than refactor it into the interface | The read-only + mutating paths were adversarially verified and shipped (v0.6.0/0.7.0); wrapping preserves those guarantees and localizes fleet logic | Rewrite `codex_bridge` as a `CodexExecutor` (rejected: churns verified, released code for no behavior gain) |
| 2026-07-23 | STANDARD mode, no verifier subagent | Read-only status wrapper over already-FULL-verified code; the only real risk (staged-treated-as-real) is covered by explicit tests | FULL mode (rejected: no new mutating/security surface) |
