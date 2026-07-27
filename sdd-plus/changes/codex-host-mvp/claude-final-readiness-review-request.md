# Final Codex-host readiness and live-dogfood review

Act as Codex's independent Claude Opus 5 architectural and security peer.
This is a read-only evidence review. Do not authorize, request, or imply edits,
commits, merges, publication, archive, release, deployment, or personal plugin
changes.

## Identity and scope

- Repository: `C:\Users\Daniel Paez\drydock`
- Branch: `codex/codex-host-mvp-checkpoint`
- Prior Opus correction-convergence tip: `79cb83f`
- Pushed review tip: `f1d9d9b3941f52f89a35cc6575a296f3fbd88848`
- Review the exact delta `79cb83f..f1d9d9b`.
- First verify that `f1d9d9b` is an ancestor of the checked-out branch. Any
  later branch commit may change only this relay and packet evidence about the
  failed review transport; report a blocker if later source, test, spec, or
  implementation changes are present outside that bounded metadata.
- The prior round accepted the explicit readiness probe, bounded recent
  PreToolUse activity, 10-second maximum age, 2-second future-skew,
  linked-path rejection, and unsigned/in-window replay disclosure for a
  cooperative, non-managed, user-disableable profile. It authorized
  exact-digest install and live dogfood only.

## Review questions

1. Do the post-convergence source and test changes preserve that accepted
   mechanism while closing the precision gaps: current model and permission
   from fresh activity, exact tokenized probe recognition, post-allow marker
   write, payload event binding, apply_patch non-marking, linked/junctioned
   activity rejection, exact time boundaries, and decoded definition digest
   chain?
2. Does the supplied live evidence honestly close the exact-handler dogfood
   task without implying managed trust, universal coverage, hostile-agent
   attestation, or `ready_for_enforcement`?
3. Is the stale Desktop backend reload finding and operator remedy accurately
   scoped to the tested Windows build?
4. One large multi-file `apply_patch` later failed closed with the generic
   bootstrap integrity message. The failed invocation made no changes. Direct
   SHA-256 immediately afterward matched installed and source `runtime.py` to
   `a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`,
   their text compared equal, and smaller guarded `apply_patch` invocations
   succeeded. Treat the cause as unresolved. Decide whether this is a blocker,
   gap, risk, or required follow-up; do not relabel it as detected tamper.
5. Search the supplied delta and current sources for a concrete false-positive
   or false-negative path, freshness replay stronger than disclosed,
   integrity or TOCTOU regression, evidence/state transition that can become
   green without support, or a claim stronger than the mechanism.

## Exact live evidence

- Installed cache matched all 22 source files at commit `d4d6311`.
- Handler revision:
  `a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`.
- Fresh task: `019fa3ba-1935-7e73-87da-6587d087ea2a`.
- `active_task_liveness`: `current_revision_observed`.
- `activity_age_ms`: `363`.
- `activity_event`: `PreToolUse`.
- `activity_tool`: `Bash`.
- `model`: `gpt-5.6-sol`.
- `permission_mode`: `bypassPermissions`.
- `model_and_permission_source`: `fresh_PreToolUse_activity`.
- `runtime_sha256` exactly matched the handler revision.
- `project_root` exactly matched `C:\Users\Daniel Paez\drydock`.
- `freshness_window_ms`: `10000`.
- `future_skew_ms`: `2000`.
- `authentication`: `none_unsigned_user_writable_plugin_data`.
- Readiness retained `active: false`, `trusted: unknown`, `managed: unknown`,
  empty `covered_tool_paths`, and `ready_for_enforcement: false`.
- Bash denied the inert command
  `Set-Content -WhatIf -LiteralPath '.env.drydock-a04c-live-probe' -Value
  'probe'` with the exact Drydock secret-path reason.
- `apply_patch` denied Update File against that guaranteed-absent path with the
  same reason.
- Final `Test-Path` returned exit 0 and `False`.
- Subsequent benign smaller packet `apply_patch` calls succeeded.
- Packet verification after recording evidence: 38 complete, 2 pending. The
  two remaining tasks are this independent review and one integrated
  end-to-end hosted workflow.
- Sync: 11/11.
- No release or publication is authorized.

## Required repository inspection

Use the repository tools available in the existing Drydock Claude chat. Do not
trust this relay or Codex's evidence summary without checking the current Git
tree and the exact committed delta. At minimum:

1. Read `AGENTS.md`, `PROJECT_CONTEXT.md`, this request, the prior
   `claude-readiness-review-result.md`, the three packet delta specs, and the
   current result section of `verification.md`.
2. Inspect `git diff 79cb83f..f1d9d9b` and the current implementations in
   `adapters/codex/drydock/hooks/runtime.py`,
   `adapters/codex/drydock/scripts/hook_runtime_source.py`, and
   `adapters/codex/drydock/scripts/drydock_codex.py`.
3. Decode or otherwise verify that the installed-definition digest chain
   described by the tests binds the current runtime bytes; do not accept the
   generated `hooks.json` description alone.
4. Reproduce the focused hook/readiness tests and packet verification when the
   local environment permits. Record any command that cannot be reproduced as
   a gap or blocker according to impact.
5. Audit the live evidence as point-in-time reported evidence. It is acceptable
   to verify its internal consistency without pretending a past event can be
   rerun retroactively.

Two authenticated automated CLI attempts supplied the review bundle but
returned `error_max_budget_usd` before a schema-valid envelope. They are
transport failures, not review verdicts, and supply no positive model or
convergence evidence.

Set `converged: true` only if there is no blocking concern. Put non-blocking
availability, diagnostic, portability, or release-operation issues in gaps or
risks. Return only:

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
