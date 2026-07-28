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
| 2026-07-28 | Replace schema v1 with strict schema v2 and refuse v1 without migration | No live v1 data exists, and silent compatibility would preserve ambiguous parsing, provenance, and aggregation semantics | Auto-read or silently migrate v1 |
| 2026-07-28 | Count one execution/result once while accepting many bound observations over time | Peer and verifier evidence can arrive in the initial batch or later; only the first accepted binding owns status, duration, token, and cost samples | Treat every observation as a new execution sample |
| 2026-07-28 | Persist every submitted source triple and its deterministic acceptance or typed rejection decision | Full envelope, result, and observation contracts permit byte-for-byte replay; scalar deltas and snapshots alone cannot prove derivation or preserve conflicts | Persist only aggregate deltas; discard duplicate/conflicting submissions |
| 2026-07-28 | Bind observations to run ID plus canonical full-envelope and full-result SHA-256 digests | A later observation must identify the exact already-recorded execution/result, and comparison scope must not vary by caller | Bind only delegation ID; compare selected fields |
| 2026-07-28 | Partition duration, token, and cost aggregates by trusted runtime status and partition token/cost aggregates by their declared evidence basis | Combining successes with failure/timeout/cancellation or mixing reported and estimated usage creates misleading totals and denominators | Keep one total duration/token/cost field |
| 2026-07-28 | Treat model terminal and error assertions as explicitly untrusted in-band claims; keep controller runtime status separate | A bare `terminal_status` or `error_summary` loses provenance and can be mistaken for trusted controller evidence | Continue persisting unqualified assertions |
| 2026-07-28 | Use a 30-second single-writer lock budget, no lock registry/cache, and mutation-free reads | The store is not a concurrent database; full verification remains mandatory, while read-only inspection must not create state | Unbounded lock registry; trust cache; read methods that create lock files |
| 2026-07-28 | Repair only an explicitly classified final torn tail through an immutable external intent and digest-bound atomic replacement | Normal operations must fail closed; intent-first ordering preserves audit evidence and makes post-crash replay decidable | Automatic truncation; append repair audit to the damaged log; repair without expected digest |
