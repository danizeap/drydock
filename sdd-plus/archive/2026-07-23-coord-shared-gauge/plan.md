# Plan

## Change

coord-shared-gauge

## Approach

1. `scripts/conductor/coord.py` (stdlib only):
   - `_state_dir()` — `%LOCALAPPDATA%\Drydock\fleet` (Windows) / `$XDG_STATE_HOME/drydock/fleet` (POSIX), `DRYDOCK_STATE` override; returns None on failure → fail open. Off `~/.codex` and (via LocalAppData) off OneDrive.
   - `_atomic_write` — mkstemp in the state dir + `os.replace` + a `PermissionError` retry loop (Windows AV/indexer transient locks).
   - `_try_acquire_refresh`/`_release_refresh` — best-effort single-flight: `O_EXCL` create a `tank-<n>.refresh.lock`; if held and older than `_STALE_LOCK_S` (30s, > the ~25s read timeout) steal via atomic replace + ownership confirm; NOT mutual exclusion (worst case a couple refresh at once = today).
   - `get_gauge(executor, ttl=75)` — cache hit within TTL → serve (age-adjust the reset countdown, tag `as_of_age_s`+`source`); else single-flight refresh → real `executor.read_remaining()` → cache; if a peer holds the lock → serve slightly-stale cache; on ANY error / disabled / no-state-dir → `_direct(executor)` (today's behavior). Only `ok:true` reads are cached; only real numbers served.
2. `executors.status()` routes the fuel read through `coord.get_gauge(self)`, itself wrapped to fall back to `read_remaining()` if coord is absent.
3. `tests/conftest.py` autouse fixture pins `DRYDOCK_STATE` to a per-test temp dir — no test touches the real cache.
4. Tests `tests/test_coord.py` + a live cold→warm proof.

## Files Expected To Change

- NEW `scripts/conductor/coord.py`, `tests/test_coord.py`
- `scripts/conductor/executors.py` (route status fuel through coord)
- `tests/conftest.py` (state isolation)
- NEW delta `sdd-plus/changes/coord-shared-gauge/specs/codex-conductor.md`

## Risks

- **A coordination bug bricking a session** — the cardinal sin. Mitigated: every `get_gauge` path is wrapped `except Exception -> _direct`; the kill switch + None-state-dir + disabled all short-circuit to a direct read. Tested.
- **Fabricated numbers** — avoided by construction: no fuel-% reservation; only real reads cached; reset countdown age-adjusted; `source`/age surfaced.
- **Cross-platform (Windows `os.replace`)** — retry loop; residual edge cases degrade to independent operation.
- **Test pollution of the real cache** — fixed by the conftest isolation (found + fixed during the live demo).

## Rollback

All new files + two additive edits (both fail-open). `git revert` clean; `DRYDOCK_COORD_DISABLE=1` disables at runtime without a revert. No change to the guards, the read-only/mutating delegation, or the executor read logic itself.
