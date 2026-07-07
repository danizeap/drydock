# Decision Log

## Change

audit-debt-polish

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-07 | Recover the audit findings from the transcript before editing | A compacted memory is unreliable; the first "already fixed" file (backend) proved several items were resolved out-of-band | Trusting memory and editing blind (rejected — would have invented or duplicated fixes) |
| 2026-07-07 | Fix the explore collision by renaming the skill to `explore-mode`, keeping the `/drydock:explore` command | Mirrors the existing `spec-sync` ↔ `/drydock:sync` precedent; distinct skill/command ids remove the duplicate `drydock:explore` registration | Fold skill into command (loses auto-load by description); drop the command (breaks muscle memory) |
| 2026-07-07 | Push the collision guarantee into the deterministic tier via a test | Drydock's own thesis: anything that must always hold belongs above advisory prose; prevents recurrence on the next skill/command added | Leave it as a one-time prose fix (rejected — no guard against regression) |
| 2026-07-07 | Adopt the Owner's out-of-band decision that `backend` owns deployment/CI/infra | The Owner edited `backend`'s description between turns to claim deployment (pairing with mcp-ranger + launchguardian); a single owner is cleaner than the three-way split I had drafted | Keep my draft note (mcp-ranger/database-steward/launchguardian, no backend) — rejected: contradicts the Owner and re-opens the "no owner" ambiguity |
| 2026-07-07 | Reconcile, not revert: make every routing doc consistent with backend-owns-deployment | Owner changed `backend` skill + I aligned AGENTS (×2), operator guide, and the deployment note | Leaving my note as-was (rejected — would contradict the Owner's skill edit) |
| 2026-07-07 | Fold the `CLAUDE.md` "two hooks → five hooks" correction into this packet | Same undersell-the-guardrails defect class as the README; both CLAUDE.md copies misinformed agents about which hooks exist | Defer to a separate packet (rejected — trivially correct, same sweep, low risk) |
| 2026-07-07 | No delta specs for this packet | No capability behavior changes — advisory/docs tier plus one additive regression test | Author delta specs (rejected — framework-theater; nothing durable to spec) |

## Out-of-band note

`skills/backend/SKILL.md` (manual-verification alignment + deployment-in-description) and `skills/spec-sync/SKILL.md` (idempotency vs stop-and-ask no-op clause) were authored by the Owner between turns and were present, uncommitted, when this packet began. They were verified as correct and are carried into this packet's commit; they are not the work of this session's agent.
