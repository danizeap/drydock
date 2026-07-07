# Plan

## Change

audit-debt-polish

## Approach

1. Recover the exact audit findings from the session transcript rather than trusting a compacted memory (this caught that backend/testing and spec-sync were already resolved on disk by the Owner, and prevented inventing edits).
2. Rename the `explore` skill to `explore-mode`: update the frontmatter `name:` and `commands/explore.md`'s skill reference first (the only correctness-critical spots — auto-loading keys off `description:`, not `name:`), then `git mv` the directory, then swap the skill-id in the routing tables (AGENTS.md ×2, operator guide) and the README skill list.
3. Add `tests/test_skill_command_registry.py` to push the collision guarantee into the deterministic tier: no skill id == a command id, and every skill's `name:` equals its directory.
4. README: rewrite the safety-layer paragraph for accuracy (5 hooks, incl. shell-redirection coverage) and add an "It governs itself" paragraph for the three autonomy hooks + fail-toward-silence.
5. Graduation notes on `architect` (compact vs full blueprint by mode) and `mcp-ranger` (risk-class → LITE/STANDARD/FULL bridge).
6. Reconcile deployment routing with the Owner's out-of-band decision (owner = `backend`) across AGENTS.md (+ scaffold), the operator guide backend row, and the AGENTS deployment note.
7. Correct the hook count in both `CLAUDE.md` copies (same undersell as the README).
8. Keep both dual-copy pairs (AGENTS.md, CLAUDE.md) byte-identical; verify with `check_sync`.

## Files Expected To Change

- `README.md` — hooks/autonomy rewrite, skill-list id.
- `skills/explore/SKILL.md` → `skills/explore-mode/SKILL.md` (rename + `name:`).
- `commands/explore.md` — skill reference.
- `AGENTS.md` + `assets/project-scaffold/AGENTS.md` — explore-mode row, backend row, deployment note (kept identical).
- `docs/AI_OPERATOR_GUIDE.md` — explore-mode + backend routing rows.
- `skills/architect/SKILL.md`, `skills/mcp-ranger/SKILL.md` — graduation notes.
- `CLAUDE.md` + `assets/project-scaffold/CLAUDE.md` — hook count (kept identical).
- `tests/test_skill_command_registry.py` — new regression guard.
- (Owner, out-of-band, verified not authored here: `skills/backend/SKILL.md`, `skills/spec-sync/SKILL.md`.)

## Risks

- Incomplete rename could break skill invocation. Mitigated: auto-load keys off `description:`; the only by-name reference is the command body (updated); a repo-wide grep confirms no orphaned skill-id refs outside the frozen archive; a new test fails if `name:` and directory ever drift.
- Dual-copy drift from editing AGENTS/CLAUDE. Mitigated: identical edits applied to both, `check_sync` gate.
- Reintroducing the deployment-ownership ambiguity the audit killed. Mitigated: aligned every doc to the single owner (`backend`) the Owner chose.

## Rollback

Pure docs + a rename + an additive test. Revert the packet's commits; `git mv skills/explore-mode skills/explore` and restore the `name:` to undo the rename. No runtime state, no data, no guardrail behavior involved.
