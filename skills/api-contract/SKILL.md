---
name: api-contract
description: Design and review API and interface contracts before implementation depends on them. Use for new, modified, deleted, internal, external, webhook, agent/tool, or client-facing endpoints — covering request/response shape, auth, object authorization, errors, data exposure, pagination, idempotency, versioning, and breaking-change impact.
---

# API Contract Skill

Answers: is this API boundary clear, permissioned, stable, testable, documented, and safe for every caller that depends on it? Runs after `architect` planning and before `backend`/`frontend` work depends on the boundary.

## Preflight

State: existing API pattern found; contract owner; intended consumers; contract change type (new / additive / breaking / deprecation / webhook / agent-tool); compatibility expectation; stop conditions.

## Core rules

- **No phantom endpoints.** Every endpoint must be explainable as "this endpoint exists so that [actor] can [action] on [resource]" — otherwise BLOCKED.
- **Follow the existing envelope.** Inspect route naming, grouping, request/response/error envelopes, auth middleware, and pagination conventions; do not invent a new response shape when the project has one. If no pattern exists, define the smallest clear contract and mark the new convention explicitly.
- **Classify every exposed field** as public / authenticated / owner-only / internal-never-exposed. Over-exposure is a contract bug, not an implementation detail.
- **Define client failure behavior**: what callers see on validation failure, auth failure, missing object, and server error — without leaking internals or confirming existence of objects the caller cannot access.
- **Idempotency and retries**: state-changing endpoints define what happens when the same request arrives twice.
- **Webhooks**: define signature verification, event versioning, retry/duplicate expectations, and what acknowledgment means.
- **Agent/tool APIs**: an endpoint callable by an AI agent is a privileged surface — define its scope and approval expectations explicitly (see `mcp-ranger`).
- **Breaking changes** require: identification of every affected caller, a versioning or migration path, and a deprecation plan. A breaking change with unidentified callers is BLOCKED.
- **The contract is an artifact** (spec section, OpenAPI fragment, or typed schema) committed with the change — not a chat message.

## Blocking rules

BLOCK if: an endpoint cannot be tied to a named workflow/screen/job/agent action; auth or object-authorization expectations are undefined; field exposure is unclassified for sensitive data; error behavior is undefined; a breaking change lacks affected-caller analysis or a migration path; a webhook lacks verification expectations; or the contract exists only in conversation.

## Evidence

STANDARD: compact format plus contract change type, endpoint inventory, auth/authorization contract, field exposure classification, and breaking-change/caller impact. FULL adds: request/response/error contracts in full, pagination/filtering, idempotency, deprecation plan, frontend and backend handoffs, Owner Summary.
