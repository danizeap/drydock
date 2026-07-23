# Brief

## Change

coord-shared-gauge — multi-chat coordination, phase 0+1 ("Shared Dipstick"): a daemon-free, fail-open, per-tank gauge cache so N concurrent Claude Code chats sharing ONE Codex account stop each spawning `codex app-server` against shared `~/.codex`. They share one TTL-cached, single-flight gauge read instead of stampeding.

Intake: Mode STANDARD (read-only cache; no gating, no mutation) — but with a `verifier` pass because cross-process/cross-platform concurrency is subtle. Primary skill: `backend`. Approvals: Owner directed the build after a design workflow (5 approaches, adversarially critiqued, synthesized). Stop conditions: any path where a coordination bug can raise into or block a delegation (must fail open); any FABRICATED number (e.g. a "reserved fuel %"); any write to `~/.codex` or the repo.

## What this means for your product

Run several chats at once on different repos, all on one Codex subscription, and they stop fighting over the fuel gauge. The first chat to check fuel this window does the real read; the others reuse it — fewer app-server spawns, fewer collisions, and every number they see is real (tagged with its age), never invented.

## User Need

Concurrent chats share one Codex tank but are blind to each other: each independently reads the gauge (spawning app-server on shared `~/.codex`) and delegates. The design panel's verdict: share the gauge honestly + meter concurrency — and specifically do NOT reserve fuel-% (the gauge is integer-percent-of-a-weekly-window; per-turn burn is sub-1% and unquantifiable in %, so any reservation is fabricated and, worse, fails silently). This packet ships the honest, highest-value, lowest-risk half: the shared gauge.

## Scope

In scope: `scripts/conductor/coord.py` — state dir off `~/.codex`/OneDrive (`%LOCALAPPDATA%\Drydock` / `$XDG_STATE_HOME`), atomic writes (temp + `os.replace` + Windows `PermissionError` retry), `DRYDOCK_COORD_DISABLE` kill switch, and `get_gauge(executor, ttl=75)` — a per-tank TTL cache with best-effort single-flight refresh (O_EXCL lock + stale-lock steal) that ALWAYS falls back to a direct read on any error and adjusts the cached reset countdown by cache age so it stays honest. Wire it into `executors.status()`. Global test isolation (`conftest` autouse `DRYDOCK_STATE`) so tests never touch the real cache. Tests + delta spec.

Out of scope (later phases): the Slot Board (concurrency metering), the N-aware conserve floor + prefer-other-tank routing, routing the delegation-path gauge (review/mutate) through the cache, Kimi, Windows Job Objects. Cross-machine coordination (single-machine/home-scoped by design).

## Acceptance Criteria

- [ ] `get_gauge` returns a fresh read on cold, a shared cache hit within TTL, and NEVER raises — any error (read failure, unwritable state, disabled) falls back to a direct read.
- [ ] Two back-to-back fleet reads spawn ~1 real gauge read, not 2 (proven live: fresh then cache).
- [ ] The cache stores/serves only REAL numbers, tagged with `as_of_age_s` + `source`; the reset countdown is adjusted by age (no fabricated values).
- [ ] A stale refresh lock is stealable (never deadlocks); a fresh lock defers to serve slightly-stale cache.
- [ ] No test writes to the real coord state dir; full suite green.

## Impact Areas

- Backend: new `coord.py`; `executors.status()` routes the fuel read through it (fail-open).
- API: `coord.get_gauge(executor, ttl)`.
- AI/model behavior: multi-chat gauge sharing (fewer app-server spawns).
- Operations/security: disposable local state outside `~/.codex`/repo; kill switch; fail-open.
- Documentation: delta spec + vision-note pointer to the coordination design.

## Open Questions

- Real Codex per-account concurrency limit (needed for the later Slot Board cap) — measure empirically.
- Is `%LOCALAPPDATA%` reliably outside OneDrive on the Owner's box? (Usually yes; verify before leaning on it.)
