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
2. Start one durable run only after an explicit Owner objective. Use
   `scripts/orchestrator.py digest-owner-action` on stdin to derive, but never
   retain, the objective and Owner-action digests; then call `start-run`.
   A resumed turn reuses that run ID. Only another explicit recorded Owner
   action may supersede it. The state is outside the repository, user-writable,
   and identifying rather than authenticated.
3. Compute the exact candidate with `scripts/orchestrator.py fingerprint`.
   Draft the smallest complete plan and send it on stdin to
   `scripts/orchestrator.py critique` with the run ID, executable-surface
   fingerprint, objective-property flags, and configured phase input/budget
   ceilings. Never put plan content or credentials in command-line arguments.
   The controller refuses an oversized request before any Claude process,
   reserves both phase and run envelopes before the model call, and records
   elapsed time, call count, input bytes, known provider cost, and unknown
   token/account usage honestly.
4. Audit the critique and its machine-readable workflow decision. A
   `converged: true` result with blockers is not convergence. Revise and run at
   most the configured round cap; unresolved blockers at the cap return to the
   Owner. Only four proven benign availability cases may return
   `workflow.action: continue_codex_only`, continue through the normal packet,
   approval, mutation, review, and verification gates in explicit `single_pilot`
   mode: authentication unavailable before spawn, an exact supported
   rate-limit marker, timeout with bounded cleanup, or a bare non-zero exit
   with no subtype/contract output plus requested-model evidence and exact zero
   cost. Budget, policy/refusal/context-limit, unknown subtype, malformed
   output, model mismatch, and missing/unknown/positive cost return to the
   Owner. Record the peer stage and
   `peer_convergence: not_established`; do not infer a retry, alternate model,
   or cross-model agreement. When the action is `return_to_owner`, stop before
   execution because the peer contract or control evidence failed.
5. Equivalent peer calls are single-flight. A live call attaches/reports; a
   fresh eligible terminal body recovers; an interrupted or stale call never
   restarts automatically. Terminal bodies are canonicalized, secret-screened,
   capped at 64 KiB, and logically expire within 24 hours. Rejected bodies
   retain only bounded digest/status metadata and may require a new
   Owner-approved call.
6. Use project-scoped nested agents only for bounded read-only advisory work.
   They are not a permission or independent-verification boundary.
7. Send every mutating task through `scripts/process_runner.py mutate`. The
   runner fixes an ephemeral `workspace-write` process to its dedicated Git
   worktree, owns Git metadata, rejects Owner-checkout drift, and never merges.
   The tested alpha CLI requires Owner config for repository trust; the runner
   reports that TCB and pins disabled MCP, web, network, rules, plugin, app,
   browser, and computer-use surfaces. A zero-exit worker with no diff is
   `no_changes`, never success.
8. Treat worker test claims as untrusted. Cross-review the staged work, then
   run `scripts/process_runner.py verify` against the exact intended tree. A
   missing, timed-out, malformed, or stale verdict is BLOCKED, never PASS.
   Read-only proves no write capability on the tested host; `-C` supplies task
   context but is not a proven read-confinement boundary.
9. Use `scripts/orchestrator.py proof-run` for candidate-bound proof. It
   materializes a fresh root from the exact clean commit, refuses tracked
   bytecode and ignored Python/pytest injection paths, and disables bytecode
   writes. Reused proof is intermediate only. Final acceptance still requires
   one `full_required_suite` record on the exact frozen executable fingerprint;
   an evidence-only record never establishes peer agreement or attestation.
10. Integrate sequentially only after the packet gates and Owner authorization
   that apply to the requested workflow. Commit, merge, push, deploy, and
   destructive cleanup remain separate actions; none is implied by a green
   verifier.
11. Report the plan/peer result, worktree and branch, changed files, evidence,
   verifier fingerprint, unresolved risks, and `merged: false` until deliberate
   integration actually occurs.

Pace routing protects the Owner's useful coding duration, not a maximum spend
cap. If remaining capacity, reset timing, or measured burn is unavailable,
report the pace forecast as unavailable and do not pretend the target is
guaranteed.
