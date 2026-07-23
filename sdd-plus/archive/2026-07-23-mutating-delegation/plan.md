# Plan

## Change

mutating-delegation

## Approach

`scripts/conductor/mutate.py` — the ONE conductor path that enables Codex writes, confined to an isolated worktree, never merging:

1. `create_worktree(base, task)` — `git worktree add <tmp> -b codex/<slug>-<id> <base>`; returns (worktree, branch) or a structured error.
2. `delegate_mutation(core, worktree, task, model)` — `codex exec -C <worktree> -s workspace-write` (the deliberate write-enabled call; validated model; JSONL usage). Reuses `codex_bridge` discovery/routing/gauge; does NOT go through the read-only `delegate()` (that lock stays intact).
3. `extract_changes(worktree, base)` — stage all in the worktree, diff `--cached` vs base → (files, diff).
4. `run_tests(worktree, test_cmd)` — optional; returns `{ran, pass, output_tail}` or None.
5. `assess_gate(files, test_result)` — **applicability-first**: no files → empty; docs/config-only → N/A (clears, never a false fail); code change → tests must be green (else blocked/red). `clears` = deterministic gate satisfied; Claude review still required.
6. `mutate(...)` — orchestrates; returns `{worktree, branch, diff, files, tests, gate, clears_gate, merged:false, note}`. Keeps the worktree on a reviewable result; cleans up on empty/failed delegation. `cleanup_worktree` removes only the temp worktree and a `codex/` branch — never anything else.

No auto-merge; no `/drydock:` command yet (library + CLI first). The merge is a separate, reviewed, Owner-gated step.

## Files Expected To Change

- NEW `scripts/conductor/mutate.py`
- NEW `tests/test_mutate.py`
- NEW delta `sdd-plus/changes/mutating-delegation/specs/codex-conductor.md`

## Risks

- **Write escaping isolation** — mitigated: `workspace-write` sandbox + a dedicated worktree + `-C <worktree>`; the base branch is never the write target; tests assert the main tree is untouched and HEAD is unadvanced.
- **Accidental branch/tree deletion in cleanup** — mitigated: cleanup removes only the temp worktree and a branch that starts with `codex/`; a test proves a non-codex branch survives a spoofed cleanup call.
- **Rubber-stamped merge** — out of scope for code (a human/Claude judgment); mitigated by design (no auto-merge, green-gate makes review cheap) and named in the brief red-team.
- **Test-command trust** — `run_tests` runs a caller-provided command via shell in the worktree; the caller (Claude/Owner) supplies it.

## Rollback

All new files. `git revert` clean; the module is inert unless invoked and cannot merge. No change to the read-only conductor, the guards, or the enforcement bridge.
