# Brief

## Change

mutating-delegation — let Codex do work that CHANGES files, safely: it writes in an isolated git worktree (sandboxed + guarded by the enforcement bridge), and an applicability-first gate plus Claude's diff review stand between that work and the main branch. **No auto-merge in v1** — the tool prepares + gates; the merge is a deliberate reviewed step.

Intake: Mode **FULL** (Codex gains write capability — the highest-risk surface in the multi-agent vision). Primary skill: `backend`; supporting: `testing`, `mcp-ranger`. Approvals: Owner chose model **A-done-right** (isolated worktree + merge-gate) over B, north star "maximize usage / code all day". Stop conditions: any path that writes to the Owner's working branch without a review gate; any auto-merge in v1; any gate that fails a task it does not apply to; any un-cleaned worktree leak.

## What this means for your product

Codex stops being read-only. It can implement a bounded task end-to-end — write, run tests, fix itself — on *its own* usage, in a sandbox that can't touch your real branch. Claude reviews the resulting diff against an applicability-first gate and merges only what passes. Two tanks burning in parallel; a single reviewed door onto `main`.

## User Need

The read-only conductor proves delegation works but can't change code. The Owner wants Codex's intelligence doing real implementation to multiply throughput (the "army of coders"), without multiplying the trust surface where mistakes are irreversible.

## Design (the safe shape of "A")

1. **Isolation.** Codex writes in a dedicated worktree/branch (`git worktree add <dir> -b codex/<task> <base>`), sandbox `workspace-write`. It cannot write outside the workspace, and its branch is not the Owner's branch.
2. **Guarded.** The `.codex/` enforcement bridge still fires inside the worktree (secrets, destructive-git) as defense-in-depth.
3. **Applicability-first gate.** Before pass/fail, the gate asks *does this apply?* — code/behavior change → tests must be green (hard, deterministic block if red or not-run); docs/config-only → test gate is **N/A** (a clean pass, never a false fail), routed to a lighter diff review; high-risk paths → MORE gates, not fewer. N/A is a first-class outcome distinct from FAIL (the LaunchGuardian applicability doctrine, applied to merges).
4. **Claude reviews the diff.** The deterministic gate is necessary, not sufficient — Claude audits the diff for scope/security/architecture (judgment the tests can't carry) before merge.
5. **No auto-merge (v1).** `mutate.py` returns `{worktree, branch, diff, files, gate_verdict, mergeable}`. The actual `git merge` is a separate, reviewed step (Owner-gated for high-risk). Auto-merge is a later increment earned by trust.

## Red-team (design, before code)

- **"The bridge has a gap, Codex writes a secret/bad file."** → Contained: the write lands in an *isolated branch*, never `main`; Claude reads the diff before merge; the git pre-commit backstop catches secrets at commit. Isolation demotes a bridge gap from "live wound" to "caught at review."
- **"Codex `git reset --hard` / force-pushes / rewrites history."** → Destructive-git is denied by the bridge; and it would only affect the *worktree branch* anyway, not `main`. Merge into `main` is done by Claude, not Codex.
- **"The gate false-fails a docs-only change for having no tests."** → The exact trap the Owner named: prevented by applicability-first — no code change → tests N/A → not a failure.
- **"Reviewer rubber-stamps to go fast (code-all-day pressure)."** → The real residual risk. Mitigated by making the review cheap (tests carry correctness so Claude only judges scope/security on a *green* diff) and by keeping tasks bounded (small diff = honest review). Named, not hidden.
- **"Worktrees leak / conflict with the Owner's tree."** → Each worktree is its own dir + branch; `mutate.py` cleans up on completion; conflicts are surfaced at merge, never silently resolved.
- **"Codex runs a destructive shell command outside the workspace (network, global install)."** → `workspace-write` sandbox constrains writes to the workspace; shell reach beyond is a known sandbox-trust boundary (documented; an OS sandbox is the layer for hard containment, per the Codex hooks caveat).

## Scope

In scope (v1): `scripts/conductor/mutate.py` — create/cleanup worktree; delegate a `workspace-write` task; extract the diff + changed files; run an optional test command; apply the applicability-first gate; return a structured verdict. Tests (fake Codex + real git worktrees in a temp repo, no quota). Delta spec. NO auto-merge; NO command wiring yet (CLI + library first).

Out of scope: auto-merge; parallel multi-task orchestration; conflict auto-resolution; the `/drydock:` command (a fast-follow once the primitive is trusted).

## Acceptance Criteria

- [ ] Codex's writes occur only in an isolated worktree/branch; the Owner's branch is never written by the delegation.
- [ ] The gate is **applicability-first**: a docs/config-only change is N/A (pass), a red or not-run test on a code change is a hard block, and N/A is a distinct outcome from FAIL.
- [ ] `mutate.py` never merges; it returns a structured verdict + the diff for review. Worktrees are cleaned up (even on failure).
- [ ] Every outcome is structured JSON (no bare traceback). Tests pass with zero Codex quota (fake); full suite green.
- [ ] Verifier confirms: no write to the base branch, no auto-merge, applicability-first holds, worktrees don't leak, fail-safe throughout.

## Impact Areas

- Backend: new `mutate.py` (worktree orchestration + gate); reuses `codex_bridge`.
- API: `mutate()` contract; the applicability-first gate function.
- AI/model behavior: Codex gains sandboxed write capability, gated.
- Operations/security: **highest-risk surface** — isolation + deterministic gate + human/Claude review + no auto-merge. FULL mode, verifier-reviewed.
- Documentation: delta spec + operator-guide note (at command wiring / release).

## Open Questions

- Test-command discovery per project (v1: explicit `--test-cmd`; auto-detect later).
- When auto-merge is earned: deferred to a trust-gated fast-follow.
