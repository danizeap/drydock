---
name: drydock-orchestrate
description: Pilot a governed Drydock plan through Claude peer critique, right-sized execution, cross-review, and separate verification. Use when the Owner asks Codex to run the full Drydock workflow.
---

# Orchestrate a Drydock change from Codex

Codex owns the control plane and side-effect authority. Claude/Opus is an
epistemic peer: it may block a plan, but its output cannot authorize tools.
The Claude adapter exposes only its schema-return `StructuredOutput` tool;
shell, file, web, MCP, Chrome, and other side-effect tools remain unavailable.
Safe mode plus strict empty MCP configuration prevents local customization or
configured MCP servers from widening that allowlist.
Its permission mode is `default`, not plan mode: plan mode changes turn
semantics, while the explicit one-tool allowlist is the authority boundary.

1. Orient the repository with the readiness and lifecycle skills. Stop before
   meaningful work when project context is missing or the change lacks the
   required packet/approval.
2. Draft the smallest complete plan. Send it on stdin to
   `scripts/orchestrator.py critique`. Never put plan content or credentials in
   command-line arguments.
3. Audit the critique. A `converged: true` result with blockers is not
   convergence. Revise and run at most the configured round cap; unresolved
   blockers at the cap return to the Owner.
4. Use project-scoped nested agents only for bounded read-only advisory work.
   They are not a permission or independent-verification boundary.
5. Send every mutating task through `scripts/process_runner.py mutate`. The
   runner fixes an ephemeral `workspace-write` process to its dedicated Git
   worktree, owns Git metadata, rejects Owner-checkout drift, and never merges.
   The tested alpha CLI requires Owner config for repository trust; the runner
   reports that TCB and pins disabled MCP, web, network, rules, plugin, app,
   browser, and computer-use surfaces. A zero-exit worker with no diff is
   `no_changes`, never success.
6. Treat worker test claims as untrusted. Cross-review the staged work, then
   run `scripts/process_runner.py verify` against the exact intended tree. A
   missing, timed-out, malformed, or stale verdict is BLOCKED, never PASS.
   Read-only proves no write capability on the tested host; `-C` supplies task
   context but is not a proven read-confinement boundary.
7. Integrate sequentially only after the packet gates and Owner authorization
   that apply to the requested workflow. Commit, merge, push, deploy, and
   destructive cleanup remain separate actions; none is implied by a green
   verifier.
8. Report the plan/peer result, worktree and branch, changed files, evidence,
   verifier fingerprint, unresolved risks, and `merged: false` until deliberate
   integration actually occurs.

Pace routing protects the Owner's useful coding duration, not a maximum spend
cap. If remaining capacity, reset timing, or measured burn is unavailable,
report the pace forecast as unavailable and do not pretend the target is
guaranteed.
