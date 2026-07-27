# Decision Log

## Change

adaptive-delegation-ledger

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-27 | Adapt ZeroHandoff's frozen/shadow/commit mechanics but replace interpersonal trust with task-specific capability evidence | The state mechanics are strong; binary acceptance and emotional dimensions are too noisy and anthropomorphic for governance | Copy its ten-dimensional relationship vector; reject all learning |
| 2026-07-27 | Store raw counts and aggregates, not one reliability authority score | Future schedulers can apply conservative, versioned policy without making the evidence store itself authoritative | Persist a scalar trust/reward score |
| 2026-07-27 | Learned evidence may recommend routing but cannot authorize effects, waive gates, select verification independence, prove convergence, or override the Owner | Usage and outcomes are advisory and can be stale, biased, or manipulated | Let the highest score control the run |
| 2026-07-27 | Persist digests and bounded metadata, never raw prompts, file contents, provider bodies, credentials, or account identifiers | The ledger is long-lived local evidence and must not become a secret/content archive | Persist full traces for convenience |
| 2026-07-27 | Use an append-only hash chain while explicitly denying authenticity and suffix-truncation claims | An unkeyed local chain detects mutation/reordering within the observed file but is user-writable and has no external tail anchor | Call SHA-256 signatures; omit integrity checks |
| 2026-07-27 | Require a controller-recorded `verified` terminal assertion, safe evidence reference, and unchanged frozen start before committing profile learning | A failed or concurrently superseded run must not train future routing, but this local store cannot prove evidence origin, pass status, or process independence until live integration binds the verifier result | Claim the reference itself proves independent verification; commit after implementation or peer acceptance |
| 2026-07-27 | Carry immutable source contracts in each shadow and recompute the exact snapshot at commit | Monotonicity alone allowed caller-constructed observations to smuggle fabricated aggregate totals into a one-sample transition | Trust caller-provided aggregate values; authenticate same-process Python objects |
| 2026-07-27 | Keep Claude-dependent work as explicit pending gates | Claude is currently quota-unavailable; local deterministic work can continue without fabricating cross-model review | Block all local work; silently treat Codex self-review as cross-model review |
