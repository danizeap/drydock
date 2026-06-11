---
name: backend
description: Disciplined backend implementation and review. Use for routes, API handlers, services, server actions, business logic, database queries, auth, sessions, roles, webhooks, jobs, queues, integrations, env/config, file import/export, server-side AI/RAG/agent logic, data mutation, payments, or any private/tenant data. Enforces safe, permissioned, testable, maintainable backend changes.
---

# Backend Skill

A backend change is not acceptable just because it works. It must be safe, understandable, permissioned, testable, reviewable, maintainable, and shaped so the next feature has a clear place to live. This is a development-time procedure, not a scanner — scanning belongs to LaunchGuardian. Architecture planning belongs to `architect`; contracts to `api-contract`; schemas/migrations to `database-steward`; deep test strategy to `testing`.

## Backend Change Plan (required before meaningful edits)

```md
# Backend Change Plan
Classification: read-only / data mutation / auth-permission / db-schema / job / webhook-integration / AI-RAG / config-secrets / refactor-only / mixed
Existing pattern found: (route, service, validation, error, auth, db-access, test patterns to follow)
Intended files: (and why)
Design choice: (where the logic lives and why)
Risks before coding:
Stop conditions:
```

Classification drives scrutiny: mutations need transaction/rollback thinking and tests; auth changes need negative permission tests and an ownership explanation; schema changes pull in `database-steward`; webhooks need signature verification, idempotency, retries, timeouts; AI/RAG backends need permission-scoped data access and human approval for dangerous actions; config changes keep secrets server-only with safe defaults and clear failure on missing required config.

## Structure rules

Thin routes/controllers (parse, validate, call service, respond). Business rules, orchestration, and permission-aware operations live in services/use-cases. Data access stays behind clear boundaries. No new factories, managers, abstract bases, generic repositories, or inheritance layers unless the project already uses them or complexity clearly justifies them. **No new architectural pattern without permission** when an existing pattern solves the problem. **No opportunistic refactors** — small local cleanup needed for the change is fine; large unrelated refactors are not. Prefer small reviewable diffs; touching multiple layers requires explanation. If you cannot say where future related logic should go, the structure is not clear enough.

## Ownership map (required when touching private/tenant/customer/user-owned data)

| Data touched | Owner | Access rule | Where enforced |
|---|---|---|---|

## Blocking rules

BLOCK if any of these hold:

- meaningful backend code edited without a Backend Change Plan;
- new architectural pattern or new dependency introduced without justification, or unrelated refactors performed without approval;
- private/tenant data touched and no clear ownership map can be produced;
- a route modifies data without auth, or sensitive data is accessed without object-level authorization;
- raw user input reaches SQL, command, file, or network boundaries unsafely;
- secrets hardcoded, or server env vars exposed to browser/public config;
- webhook lacks signature verification where signatures are available;
- payment/billing/business-critical logic has no validation or audit trail;
- file upload/import/export lacks validation;
- a job or repeated operation can duplicate, corrupt, delete, or overwrite data without idempotency/guardrails;
- no tests exist for meaningful behavior, or permission logic lacks negative tests without justification;
- test commands are listed but the behavior they prove cannot be explained;
- errors leak sensitive internals, or logs include secrets, tokens, PII, or private business data;
- external integration lacks timeout/retry/failure behavior;
- an endpoint or job can create unbounded queries, API calls, file processing, or LLM cost;
- AI/RAG/agent logic can access private data beyond the requesting user's permissions;
- existing contracts changed without identifying affected callers;
- hidden global/shared mutable state or cross-tenant caching introduced without isolation and invalidation;
- the diff is too large to review safely and cannot be split;
- business logic, db access, validation, and response formatting are mixed with no boundaries, or logic is copy-pasted across handlers.

## Review questions (all must be answerable before PASS)

Can I explain this change in plain English? Point to where validation happens? Where authentication happens? Where authorization happens? Where object ownership is enforced? Where business logic lives? Where database access happens? What test proves the important behavior? What could break? How to roll it back? Where future related logic should go?

## Human review required

When touching: customer/candidate/company private data, auth or authorization, payments/billing, secrets or production credentials, destructive db operations or migrations, data deletion, AI/RAG access to private data, external webhooks, deployment/config, jobs that mutate data, or integrations that send external messages/records.

## Testing expectations

Match to risk: pure function → unit; route with validation/auth → route/integration test; db mutation → integration/service test; webhook/job → duplicate-event and failure-path tests; auth/permissions → negative tests (wrong user cannot access the object); AI/RAG private data → access-control retrieval test. State test *intent* in plain English — commands alone are not enough.

## Evidence

STANDARD mode: protocol compact format (files changed, behavior changed, proof/tests with intent, risks, result, next action) plus the ownership map when applicable. FULL mode adds: change classification, route/function inventory, data inputs and validation, auth/authorization/ownership, mutation safety, secrets/config, integration behavior, AI boundary, error/logging review, performance/cost sanity, silent-behavior-change check, kill-switch consideration, negative tests, rollback notes, LaunchGuardian handoff, Owner Summary.
