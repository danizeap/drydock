# Verification

## Change

coord-shared-gauge

## Automated Checks

- [x] `python -m pytest tests/test_coord.py -q` → 10 passed: cache hit shares one read; TTL expiry refreshes; fail-open on read error; kill switch bypasses cache; age-adjusted reset countdown; stale-lock steal + refresh; fresh-lock defer + serve-stale; unwritable-state fail-open; negative countdown clamped; wrong-shape cache self-heals.
- [x] `python -m pytest -q` (full suite) → 347 passed, 3 skipped — no regressions.
- [x] `python scripts/check_sync.py` → 11 pairs identical.
- [x] Live cold→warm proof: two back-to-back `executors.py` fleet reads → run 1 `source: fresh` (real read), run 2 `source: cache` (no second app-server spawn). The multi-chat win, demonstrated.

## Manual Checks

- [x] Independent adversarial `verifier` subagent (concurrency + fail-open focus). Verdict **VERIFIED WITH NOTES**; the three cardinal invariants CONFIRMED under fuzzing of every hostile input (corrupt caches — list/scalar/wrong-type/infinity `as_of`/binary; garbage locks — empty/no-float/NUL; `read_remaining` returning None/list/int/`{ok:false}`/raising; path-traversal `.name`; a `.name` that raises): **(a)** fail-open is total (nothing raises/blocks/returns a non-dict); **(b)** no fabricated numbers (only `ok:true` reads cached, real values age-tagged, no reserved-%); **(c)** no deadlock (steal threshold 30s > the 25s read timeout; steal failure degrades to direct). Confirmed empirically that the test suite does NOT pollute the real `%LOCALAPPDATA%\Drydock` cache (sha+mtime identical before/after a full run).
- [x] Verifier notes resolved: **negative reset countdown** now clamped at 0 (`_serve`); **wrong-shape cache** now treated as absent so it self-heals on the next refresh (`get_gauge`). Both have regression tests. The remaining note (double-steal both refreshing) is within the design's declared best-effort semantics — degrades to today's behavior, no deadlock/fabrication — and is intentionally not "fixed" (fixing it would require the mutex the design deliberately rejects).

## Documentation Updates

- [x] Specs: delta `specs/codex-conductor.md` (R20–R22), to be synced into the living capability.
- [x] Project context: the coordination design lives in the design-workflow synthesis; a vision-note pointer is added.
- [ ] No documentation update needed. Reason:

## Result

VERIFIED. The Shared Dipstick ships: a fail-open, honest, daemon-free per-tank gauge cache so concurrent chats sharing one Codex account collapse N app-server reads to ~1 per window — proven live (fresh→cache), fuzz-verified fail-open, and self-isolating in tests. Later phases (Slot Board concurrency metering, N-aware floor routing, Kimi) are scoped out. Ready for `/drydock:sync` then archive.
