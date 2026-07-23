# Tasks

## Change

coord-shared-gauge

## Implementation

- [x] `scripts/conductor/coord.py` — state dir (off ~/.codex/OneDrive), atomic write, kill switch, `get_gauge` (TTL cache + best-effort single-flight + stale-lock steal + age-adjusted honest serve + total fail-open).
- [x] `scripts/conductor/executors.py` — `status()` routes the fuel read through `coord.get_gauge(self)`, fail-open to `read_remaining()`.
- [x] `tests/conftest.py` — autouse `DRYDOCK_STATE` isolation so no test writes the real cache.
- [x] `tests/test_coord.py` — cache hit shares one read; TTL expiry refreshes; fail-open on read error; kill switch; age-adjusted countdown; stale-lock steal; fresh-lock defer; unwritable-state fail-open.
- [x] Delta spec `specs/codex-conductor.md` (coordination requirements).
- [x] Run verification — coord tests 8 passed; full suite 345 passed; check_sync 11/11; live cold→warm proof (fresh then cache); then the `verifier` subagent (concurrency + fail-open).
