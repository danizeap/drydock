---
name: database-steward
description: Design and review database and storage safety. Use for schemas, migrations, indexes, constraints, seed data, imports/exports, deletion, retention, audit logs, RLS policies, tenant isolation, backups, and RAG/vector storage. Prevents unowned, irreversible, unindexed, unrecoverable, or privacy-dangerous data structures.
---

# Database Steward Skill

Answers: is this data model safe, owned, isolated, reversible, queryable, maintainable, and lifecycle-aware? Runs after `architect` planning and before `backend` work depends on the data model.

## Preflight

State: existing data pattern found; data change type (new schema / migration / index / destructive op / lifecycle / RAG-vector / seed-import-export); data owner; tenant boundary; source of truth; risk level; stop conditions.

## Core rules

- **Every table/collection has an owner concept.** Who owns each row — user, team, org, tenant? How is every query scoped to that owner? Unowned data is a blocking finding.
- **Tenant isolation is structural**, not conventional: enforced by scoped queries, RLS, or schema design — not by developers remembering a WHERE clause.
- **Migrations are reversible or explicitly accepted as one-way** with a human-approved reason. Destructive operations (drops, truncations, irreversible transforms) require explicit human approval and a tested backup/restore expectation first.
- **Indexes follow queries.** New query patterns name their index plan; unbounded scans on growing tables are findings.
- **Sensitive data is classified** (PII, credentials-adjacent, financial, health, private business data) and its retention, deletion path, and audit needs are stated. "We never delete" is a decision requiring justification, not a default.
- **RAG/vector storage is data too**: chunks carry source links and access metadata; retrieval respects the requesting user's permissions; deletion of a source deletes or invalidates derived vectors.
- **Seed/test data never contains real personal or production data.**
- **Imports/exports** validate input, bound size, and respect ownership on the way in and exposure classification on the way out.

## Blocking rules

BLOCK if: ownership or tenant boundary is undefined for any touched table; a destructive operation lacks explicit human approval or recovery expectation; a migration cannot state its reversal path or one-way acceptance; sensitive data is unclassified or has no deletion/retention answer; RAG/vector storage can serve a user data they could not access directly; seed data contains real personal data; or the source of truth for a duplicated fact is unclear.

## Human review required

Destructive migrations, data deletion, retention changes, RLS/policy changes, cross-tenant structures, backup/recovery assumptions, and anything touching production data.

## Evidence

STANDARD: compact format plus entity inventory, ownership model, tenant boundary, migration plan with reversal, and sensitive-data classification. FULL adds: index/query plan, lifecycle and deletion rules, audit trail, RLS policies, RAG/vector review, import/export safety, backup/recovery assumptions, Owner Summary.
