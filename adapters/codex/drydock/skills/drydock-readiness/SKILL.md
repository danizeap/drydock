---
name: drydock-readiness
description: Report evidence-based Drydock readiness for the current Codex repository and task. Use when the Owner asks whether Drydock is installed, active, enforcing, or ready.
---

# Report Drydock readiness

1. Resolve this plugin's root from the loaded skill and run:
   `python <plugin-root>/scripts/drydock_codex.py readiness --root <repository>
   --check-peer`. The peer check reads Claude CLI authentication status but
   does not make a model call or spend model quota. On the currently tested
   Desktop build, the CLI binds liveness from `CODEX_THREAD_ID` only when
   exactly one direct Codex plugin-data child contains a matching record for
   that task, runtime digest, and repository root. Missing, stale, malformed,
   repository-mismatched, or ambiguous records remain non-positive.
2. Report the JSON fields without strengthening them. File presence proves
   only definition presence; it does not prove trust, enablement, current-task
   liveness, coverage, or enforcement.
3. Call the lifecycle ready only when `ready_for_lifecycle` is true.
4. Call enforcement active only when `ready_for_enforcement` is true. In the
   Phase 1 shell this is deliberately false.
5. Keep hosted/specialized or unprobed tool paths explicitly uncovered.
6. Report peer authentication and operational status separately. An
   `auth_ready` result proves only that the no-quota authentication check
   succeeded; it deliberately reports operational status as `not_checked`.
   Absence of a peer failure is not peer agreement.
7. Treat `--session-id` and `--plugin-data` as explicit diagnostic overrides,
   not ordinary Owner setup. Explicit values take precedence and are still
   checked against the current runtime digest and repository root.

Ordinary plugin hooks, once added, remain non-managed and user-disableable.
Never use a Tier-4 or “cannot be reasoned around” claim without a separately
proven managed mechanism.
