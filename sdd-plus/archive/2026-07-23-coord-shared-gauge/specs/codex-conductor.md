# Capability (delta): codex-conductor

Capability: codex-conductor

Extends the conductor with multi-chat coordination (phase 0+1): a fail-open, per-tank shared gauge cache so concurrent chats sharing one account stop stampeding the app-server, while only ever serving real numbers.

## ADDED Requirements

### R20 — Shared, single-flight gauge cache; fail-open always
`coord.get_gauge(executor, ttl)` SHALL serve a per-tank gauge from a TTL cache within the window, do a best-effort single-flight refresh when stale (so N concurrent chats collapse to ~1 real read per TTL), and SHALL fall back to a direct `executor.read_remaining()` on ANY error, on `DRYDOCK_COORD_DISABLE=1`, or when the state dir is unavailable. It SHALL NOT raise into or block a delegation.

- **WHEN** the gauge is read twice within the TTL
- **THEN** the first is a real read (`source: fresh`) and the second is served from cache (`source: cache`) with no second real read

- **WHEN** the underlying read raises, coord is disabled, or the state dir can't be created
- **THEN** `get_gauge` returns a direct read (`source: direct`) and never raises

### R21 — Only real numbers, honestly aged; never a fabricated reservation
The cache SHALL store only successful reads and SHALL serve real values tagged with `source` and `as_of_age_s`, adjusting the reset countdown by the cache age. It SHALL NOT invent a reserved/allocated fuel percentage.

- **WHEN** a cached gauge is served after aging
- **THEN** `resets_in_hours` is reduced by the cache age and the age is surfaced; no value is fabricated

### R22 — No deadlock; state is off the shared/synced trees; isolated in tests
The single-flight lock SHALL be stealable once older than a threshold above the read timeout (a crashed holder never deadlocks the tank). State SHALL live outside `~/.codex` and outside OneDrive-synced trees. Tests SHALL never write to the real coordination state dir.

- **WHEN** a refresh lock is older than the stale threshold
- **THEN** another session may steal it and refresh; a fresh lock instead defers to serve slightly-stale cache
