# Verification

## Change

mutating-delegation

## Automated Checks

- [x] `python -m pytest tests/test_mutate.py -q` → 14 passed. Covers the applicability-first gate matrix (docs→n/a, code+green→green, code+red/absent→blocked, empty, mixed, extensionless-code-basename→applies); worktree isolation (main tree untouched, HEAD unadvanced); cleanup never deletes a non-`codex/` branch; `mutate()` never merges + keeps the worktree for review; code-without-tests blocks; code-green clears; no-core; and `create_worktree` returns a structured error (not a traceback) on a git spawn failure.
- [x] `python -m pytest -q` (full suite) → 324 passed, 3 skipped — no regressions; the read-only `codex_bridge` lock tests still pass (write capability did not erode the read-only path).
- [x] `python scripts/check_sync.py` → 11 pairs identical (mutate.py is plugin-level, no scaffold twin).

## Manual Checks

- [x] Independent adversarial review by the `verifier` subagent (FULL mode). Verdict **VERIFIED WITH NOTES**; the four highest-risk properties CONFIRMED against code + re-run tests: **(a)** no write to the base branch/main tree (every git op except `worktree add` runs `cwd=worktree`; HEAD unadvanced); **(b)** no auto-merge (no merge/rebase/cherry-pick/push/reset anywhere; `merged` hardcoded false); **(c)** N/A never false-fails (applicability decided before pass/fail; a non-code change cannot reach blocked/red); **(d)** cleanup blast-radius bounded (`codex/`-prefix guard undefeatable; a spoofed non-codex branch survives). Confirmed `delegate_mutation` is a separate function that does not erode the verified read-only lock, and the exception path cleans up.
- [x] Verifier notes resolved:
  - **Extensionless code false-clears as N/A** — fixed: `_CODE_BASENAMES` (Dockerfile/Makefile/…) now count as code; regression test added. Extensionless *shebang* scripts remain a documented edge (backstopped by Claude's diff review + packet_guard).
  - **`create_worktree` unstructured traceback + temp-dir leak on git-absent/timeout** — fixed: wrapped in try/except, returns a structured error and cleans the temp dir; regression test added.

## Documentation Updates

- [x] Specs: delta `specs/codex-conductor.md` (R9–R12), to be synced into the living `codex-conductor` capability.
- [ ] README/operator-guide: deferred to command-wiring / release (mutating delegation ships as a library + CLI first; the `/drydock:` command and operator-guide note are a fast-follow).
- [ ] No documentation update needed. Reason:

## Result

VERIFIED. Mutating delegation ships as an isolated-worktree, applicability-gated, no-auto-merge primitive: Codex writes in a sandboxed `codex/…` branch, the diff clears a deterministic gate that never false-fails an N/A change, and nothing merges without Claude's deliberate review. All four stop-condition properties hold under adversarial review; both notes resolved. Ready for `/drydock:sync` then archive.
