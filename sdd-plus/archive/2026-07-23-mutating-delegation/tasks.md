# Tasks

## Change

mutating-delegation

## Implementation

- [x] Red-team the design before code (embedded in brief.md).
- [x] `scripts/conductor/mutate.py` — worktree create/cleanup, `workspace-write` delegation (isolated), diff extraction, optional test run, applicability-first gate, orchestration; NO merge.
- [x] `tests/test_mutate.py` — applicability-first gate matrix; worktree isolation; cleanup-never-deletes-non-codex-branch; mutate does-not-merge + keeps-worktree + main-tree-isolated; code-without-tests blocks; code-green clears; no-core. Real git worktrees + fake Codex, no quota.
- [x] Delta spec `specs/codex-conductor.md` (mutating delegation requirements).
- [x] Run verification — mutate tests 12 passed; full suite 322 passed; check_sync 11/11; then the `verifier` subagent (FULL mode).
