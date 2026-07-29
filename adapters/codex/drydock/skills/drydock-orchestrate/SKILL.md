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

The normal Codex route has one Owner-facing task. If a separate Codex task is
deliberately used, coordinate it through the host's direct task read/send/wait
mechanisms and retain its task ID in workflow state. Asking the Owner to copy
output between Codex tasks is a disclosed degraded fallback, not the default.

1. Orient the repository with the readiness and lifecycle skills. Stop before
   meaningful work when project context is missing or the change lacks the
   required packet/approval.
2. Keep one canonical active `plan.md` in the packet. Replanning updates that
   plan in place with a positive revision and exact predecessor digest; recovery
   and negotiation artifacts are history, never competing active plans.
3. Before a durable run or provider call, create a strict workflow payload on
   stdin containing `authority` and `plan`. The authority binds an immutable
   Owner-issued objective ID independent of editable prose, the objective and
   one-time Owner-action digests, optional predecessor objective ID, canonical
   repository, current task ID, exact paths/actions, optional exact push
   destination, expiry, and resource and circuit ceilings. The compact
   technical plan declares only a subset of those fields and the exact path and
   SHA-256 of the packet's sole active `plan.md`; the controller rechecks those
   bytes before every executor admission. Owner actions are atomically consumed
   once for create, revise, blocked resume, or circuit resolution; a crash after
   consume burns the action and requires a fresh Owner action.
   Start it with `scripts/orchestrator.py workflow-start --task-id <id>`.
   Unknown fields, wildcards, stale lineage, expired authority, and any
   authority/plan mismatch fail locally without spending a model call. Manifest
   digests identify controller input; they do not prove Owner authorship.
   Stdin is primary. When the host cannot deliver a native pipeline, write the
   body under the controller's out-of-tree `payloads` directory and pass only
   `--payload-file <absolute-path> --payload-sha256 <digest>`. The child accepts
   only a canonical regular non-reparse file under that state root, bounds and
   reads it once, hashes and parses the same buffer, rechecks identity, and
   deletes it. Expired orphans are reaped. Never put the payload body in argv or
   an inherited environment variable.
   `DRYDOCK_ORCHESTRATION_CONTROL_ENABLED` accepts only `0` or `1`; `0` is a
   fail-closed rollback state that creates no governed workflow and authorizes
   no fallback execution. Every workflow record reports the enabled state.
4. Start one durable run only after the workflow preflight succeeds. Use
   `scripts/orchestrator.py digest-owner-action` on stdin to derive, but never
   retain, the objective and Owner-action digests; then call `start-run`.
   A resumed turn reuses that run ID. Only another explicit recorded Owner
   action may supersede it. The state is outside the repository, user-writable,
   and identifying rather than authenticated.
5. Compute the exact candidate with `scripts/orchestrator.py fingerprint`.
   Draft the smallest complete plan and send it on stdin to
   `scripts/orchestrator.py critique` with the run ID, executable-surface
   fingerprint, objective-property flags, and configured phase input/budget
   ceilings. Never put plan content or credentials in command-line arguments.
   The controller refuses an oversized request before any Claude process,
   reserves both phase and run envelopes before the model call, and records
   elapsed time, call count, input bytes, known provider cost, and unknown
   token/account usage honestly.
6. Admit every executor phase through `workflow-admit`, pass that exact
   admission to the official executor wrapper so it is atomically consumed
   before provider spawn or side effect, and complete it through
   `workflow-finish`. Phase order is preflight → plan peer → mutation →
   cross-review → proof → verification → integration → optional push →
   complete. Admission binds objective, workflow/run, phase, authority, plan,
   mechanism, input, prior gates, candidate, random nonce, and expiry. A
   consumed admission is burned even if the executor crashes; after expiry
   `workflow-recover-admission` records the unknown-cost crash and permits a
   newly issued admission without replaying the token. A direct invocation of
   a primitive does not advance or satisfy workflow state absent direct
   same-user tampering with controller state. This is coordination inside a
   user-writable same-user TCB, not a signature or hostile-user boundary.
7. Audit the critique and its machine-readable workflow decision. A
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
   The peer reviews technical correctness, security, contract alignment, and
   verification sufficiency. It does not interpret or widen Owner authority.
   After round one, send stable unresolved blocker IDs plus changed plan fields,
   not the complete negotiation history. `insufficient_context` is always
   non-converging, names exact additional bounded context, and is a technical
   outcome rather than a procedural failure. Every critique echoes the SHA-256
   of the exact canonical UTF-8 review bytes; a mismatch cannot converge.
8. Equivalent peer calls are single-flight. A live call attaches/reports; a
   fresh eligible terminal body recovers; an interrupted or stale call never
   restarts automatically. Terminal bodies are canonicalized, secret-screened,
   capped at 64 KiB, and logically expire within 24 hours. Rejected bodies
   retain only bounded digest/status metadata and may require a new
   Owner-approved call.
9. The objective-level circuit spans every run ID, retry, and phase before and
   after worker start. Worker start never resets it. It counts procedural
   failures, phase entries, outbound bytes, observed executor time, known
   provider spend, and unknown-cost entries. Technical blockers do not increase
   the procedural counter but still consume every observable axis. Manifest
   ceilings may narrow but cannot exceed controller safety maxima. One
   one-time-Owner-action circuit resolution is the hard maximum; a later
   opening is terminal for that objective ID.
10. Treat `pre_mutation_critique` as a machine-readable gate input and require
   its official executor admission. A required critique with
   `gate_satisfied: false`, absent convergence, input-identity mismatch, or
   insufficient context cannot produce a mutation admission.
11. Use project-scoped nested agents only for bounded read-only advisory work.
   They are not a permission or independent-verification boundary.
12. Send every mutating task through `scripts/process_runner.py mutate`. The
   runner fixes an ephemeral `workspace-write` process to its dedicated Git
   worktree, owns Git metadata, rejects Owner-checkout drift, and never merges.
   The tested alpha CLI requires Owner config for repository trust; the runner
   reports that TCB and pins disabled MCP, web, network, rules, plugin, app,
   browser, and computer-use surfaces. A zero-exit worker with no diff is
   `no_changes`, never success. In the official admitted path, the runner
   rechecks the exact review snapshot after the worker is quiescent and creates
   one clean isolated candidate commit with a v2 executable fingerprint. The
   worker still cannot stage or commit, and the Owner branch is unchanged.
13. Treat worker test claims as untrusted. Cross-review the exact isolated
   candidate commit, then
   run `scripts/process_runner.py verify` against the exact intended tree with
   the active `--packet-root` and the exact `--proof-record` emitted by the
   frozen `full_required_suite` run. Before provider spawn, the parent runner
   recomputes v2 identity and refuses a v1, intermediate, failed, timed-out,
   non-zero-exit, malformed, dirty-candidate, or fingerprint-mismatched record.
   The record is user-writable and unauthenticated: it is required but
   insufficient for PASS and does not attest execution provenance. A missing,
   timed-out, malformed, or stale verdict is BLOCKED, never PASS. Read-only
   proves no write capability on the tested host; `-C` supplies task context
   but is not a proven read-confinement boundary.
14. Use `scripts/orchestrator.py proof-run` for candidate-bound proof. It
   materializes a fresh root from the exact clean commit, refuses tracked
   bytecode and ignored Python/pytest injection paths, and disables bytecode
   writes. Reused proof is intermediate only. Final acceptance still requires
   one `full_required_suite` record on the exact frozen executable fingerprint;
   an evidence-only record never establishes peer agreement or attestation.
   Fingerprint v2 binds exact committed Git-tree paths, types, modes, and blob
   bytes. Only the exact active packet's canonical task-checkbox state is
   projected out of executable identity; its raw task bytes remain evidence,
   while task wording, ordering, noncanonical markers, templates, and other
   packets remain executable. Unsafe projection leaves the complete task file
   executable and reports why. Checkbox state can therefore change status,
   Stop, verification, or archive outcomes without changing executable
   identity. Never equate unchanged executable identity with unchanged
   governance state.
15. Integrate sequentially only after the packet gates and Owner authorization
   that apply to the requested workflow. The official `process_runner.py
   integrate` path consumes its integration admission, rechecks the clean
   unchanged Owner base and exact clean candidate, performs only a
   fast-forward, and verifies the integrated v2 identity. An ambiguous update
   is terminal rather than retried or rolled back. Candidate commit,
   integration, push, deploy, and destructive cleanup remain separate actions;
   none is implied by a green verifier. Workflow push is deliberately
   unavailable until a dedicated
   wrapper consumes the strict admission and proves the clean candidate,
   destination, remote baseline, exact pushed commit, and post-push ref.
16. Report the plan/peer result, worktree and branch, changed files, evidence,
   verifier fingerprint, unresolved risks, and `merged: false` until deliberate
   integration actually occurs.

Pace routing protects the Owner's useful coding duration, not a maximum spend
cap. If remaining capacity, reset timing, or measured burn is unavailable,
report the pace forecast as unavailable and do not pretend the target is
guaranteed.
