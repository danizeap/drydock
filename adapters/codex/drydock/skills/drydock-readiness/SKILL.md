---
name: drydock-readiness
description: Report evidence-based Drydock readiness for the current Codex repository and task. Use when the Owner asks whether Drydock is installed, active, enforcing, or ready.
---

# Report Drydock readiness

1. Resolve this plugin's root from the loaded skill and run:
   `python <plugin-root>/scripts/drydock_codex.py readiness --root <repository>
   --check-peer --hook-liveness-probe`. The peer check reads Claude CLI
   authentication status but does not make a model call or spend model quota.
   The probe flag is required for positive liveness: on the currently tested
   Desktop build, the command's supported Bash `PreToolUse` hook recognizes
   that exact readiness probe and writes a separate activity marker immediately
   before Python starts. The CLI binds
   liveness from `CODEX_THREAD_ID` only when exactly one direct Codex
   plugin-data child contains plain, non-linked SessionStart and activity
   record paths matching that task, runtime digest, and repository root, and
   the activity marker is no more than 10 seconds old or 2 seconds future-
   skewed on the operating-system wall clock. Missing, replayed, future-dated,
   malformed, repository-mismatched, linked, or ambiguous records remain
   non-positive.
2. Report the JSON fields without strengthening them. File presence proves
   only definition presence; it does not prove trust, enablement, current-task
   liveness, coverage, or enforcement. Plugin-data records are unsigned and
   user-writable; `current_revision_observed` is bounded cooperative evidence
   that the supported readiness-probe path ran immediately before readiness,
   not attestation against a hostile agent. A marker may replay within the
   documented 10-second window.
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
   checked against the current runtime digest, repository root, and fresh
   activity marker.

Ordinary plugin hooks, once added, remain non-managed and user-disableable.
Never use a Tier-4 or “cannot be reasoned around” claim without a separately
proven managed mechanism.
