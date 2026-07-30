# Claude Re-review Request

Act as the cross-model architectural peer for Drydock's Codex-host MVP.
Re-read the current repository versions of:

- `docs/CODEX_HOST_BUILD_BLUEPRINT.md`
- `PROJECT_CONTEXT.md`
- `sdd-plus/changes/codex-host-mvp/brief.md`
- `sdd-plus/changes/codex-host-mvp/plan.md`
- `sdd-plus/changes/codex-host-mvp/decision-log.md`
- all three delta specs under
  `sdd-plus/changes/codex-host-mvp/specs/`

Audit the claims against the existing `codex-conductor` living spec,
`scripts/conductor/negotiate.py`, `hooks/`, and the project-scaffold Codex
guard. Do not trust Codex's reconciliation report without checking it.

Your first three blockers were:

1. Missing worktree containment and truthful non-merging execution gates.
2. Verify-then-import TOCTOU in the hook-integrity design.
3. Unsafe reuse of Claude-name/stateful hook entry points as shared policy.

Your second review confirmed those fixes and found one new blocker: nested
write-capable agents inherit live parent permissions, so assigning them a
worktree did not enforce containment. The current revision replaces nested
mutation with a separate ephemeral `codex exec` process whose
`workspace-write` sandbox and canonical `-C` worktree root are fixed by the
runner. It also requires an atomic exclusive lease and Owner-state
fingerprinting. A live disposable probe created an in-root file while Codex
rejected a sibling Owner-checkout write as outside the project; independent
filesystem/Git checks confirmed the Owner checkout stayed unchanged.

The current revision also addresses your three gaps:

- Hook definitions use narrow explicit matchers. A mismatch inside a matched
  side-effect hook denies; an unmatched/read-only tool is not intercepted and
  readiness reports it uncovered.
- Exact source-to-bundle rebuild comparison runs in CI beside `check_sync.py`
  and repeats at release.
- The runtime is one normalized plain UTF-8 Python file with LF endings, no BOM,
  timestamps, or archive metadata, and deterministic source ordering; zip/pyz
  is excluded.

Also recheck the earlier six changes: authenticated Claude remains Phase 0;
process isolation is separate from epistemic diversity; the existing bounded
`negotiate.py` contract is preserved; the threat model is explicit; pace-first
fuel policy is recorded; and regression-first plus Windows
command-length/path proof is required.

Search for new blockers, contradictions, or claims stronger than their
mechanism. Return:

```json
{
  "converged": false,
  "overall": "one honest paragraph",
  "blocking_concerns": [],
  "gaps": [],
  "risks": [],
  "required_changes": []
}
```

Set `converged: true` only if `blocking_concerns` is empty and you would approve
implementation starting after the separate authenticated Claude CLI probe
succeeds. A convergence flag accompanied by blockers is not trusted.
