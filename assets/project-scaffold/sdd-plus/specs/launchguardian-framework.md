# LaunchGuardian Framework

## Purpose

LaunchGuardian Framework (LGF) is the SDD+ security-shipping layer for deployable projects.

It helps teams decide what security, privacy, deployment, and operational checks are required before a project is launched or materially changed. LGF is documentation-first: it records scope, applicable gates, evidence, accepted risks, and the final launch decision.

LGF does not implement a scanner, application runtime, policy engine, or automated security product by itself.

## When LGF Applies

LGF is required for deployable projects, including:

- public websites or web applications
- APIs, webhooks, workers, jobs, and services
- mobile, desktop, or CLI tools that connect to external systems
- internal tools that process sensitive, customer, production, or business-critical data
- infrastructure, deployment, authentication, authorization, database, storage, or networking changes

LGF may be skipped for documentation-only, local-only, or exploratory work when no deployable artifact, sensitive data, or persistent integration is affected. Skips should be recorded in the active SDD+ change packet.

## Framework Artifacts

Each deployable project should maintain project-specific LGF documents created from these templates:

- `sdd-plus/security/gate-applicability.template.yml`
- `sdd-plus/security/scope-contract.template.yml`
- `sdd-plus/security/product-inventory.template.yml`
- `sdd-plus/security/data-inventory.template.yml`
- `sdd-plus/security/threat-model.template.md`
- `sdd-plus/security/auth-role-matrix.template.yml`
- `sdd-plus/security/dependency-policy.template.yml`
- `sdd-plus/security/accepted-risks.template.md`
- `sdd-plus/security/launch-decision.template.md`

Projects may copy templates to non-template filenames when creating real launch records.

## Gate Model

LGF uses gates to decide which checks must be completed before launch.

Canonical LGF gates:

| Gate | Purpose |
| --- | --- |
| Gate 0 — Scope & Permission | Confirm what is being launched, who approved the review scope, and what is intentionally out of scope. |
| Gate 1 — Product, Asset & Data Inventory | Record components, exposed surfaces, assets, data classes, owners, and trust boundaries. |
| Gate 2 — Threat Modeling | Identify likely threats, abuse paths, mitigations, residual risk, and launch blockers. |
| Gate 3 — Code Security | Review security-sensitive code paths, unsafe patterns, privilege boundaries, and implementation evidence. |
| Gate 4 — Secrets & Config Hygiene | Confirm secrets, tokens, keys, credentials, and environment configuration are handled safely. |
| Gate 5 — Frontend Exposure | Review public routes, browser storage, client-side secrets, CORS, CSP, and user-controlled rendering. |
| Gate 6 — API Auth & Object Authorization | Confirm API authentication, object-level authorization, tenant boundaries, and permission checks. |
| Gate 7 — Injection & Input Safety | Review input validation, output encoding, query construction, command execution, and parser safety. |
| Gate 8 — Auth, Sessions & CSRF | Review login, signup, password reset, session lifecycle, cookies, MFA, CSRF, and logout behavior. |
| Gate 9 — File Upload, SSRF, Imports & Exports | Review file handling, remote fetches, import/export formats, SSRF controls, and content processing. |
| Gate 10 — Dependency, SBOM & Supply Chain | Review dependency policy, lockfiles, vulnerability thresholds, package sources, and SBOM expectations. |
| Gate 11 — Infrastructure, DNS, TLS & Web Hardening | Review hosting, DNS, TLS, headers, network exposure, environment separation, and web hardening. |
| Gate 12 — Resilience, DDoS, Abuse & Cost Defense | Review rate limits, quotas, retries, abuse paths, cost controls, and degradation behavior. |
| Gate 13 — Webhooks, Background Jobs & Integrations | Review webhook verification, job idempotency, retries, third-party integrations, and failure handling. |
| Gate 14 — Privacy, Legal & Data Lifecycle | Review personal data, notice/consent, retention, deletion, legal constraints, and data sharing. |
| Gate 15 — AI/RAG/Agent Security | Review prompt injection, tool/MCP permissions, retrieval boundaries, model data exposure, and agent actions. Apply the **lethal-trifecta test** (see "Gate 15 — the Lethal-Trifecta Test" below): an AI agent, MCP server, or LLM tool-chain that combines access to private data, exposure to untrusted content, and an outbound channel is high-risk regardless of RLS or read-only settings. |
| Gate 16 — Multi-Tenant & Internal Permission Isolation | Review tenant isolation, internal roles, admin access, scoped permissions, and cross-account access. |
| Gate 17 — Observability, Logs & Incident Readiness | Review logging, monitoring, alerting, sensitive log data, incident paths, and ownership. |
| Gate 18 — Backup, Recovery, Deletion & Rotation | Review backups, restore tests, deletion paths, credential rotation, and recovery objectives. |
| Gate 19 — Business Logic Abuse | Review workflow abuse, fraud paths, privilege escalation through product logic, and bypasses. |
| Gate 20 — Launch Decision | Record findings, accepted risks, skipped gates, rollback plan, and final human approval. |
| Gate 21 — Continuous Monitoring | Record post-launch monitoring, review cadence, recurring checks, and ownership. |

The agent may propose which gates apply. A human must confirm skipped high-risk gates before launch.

For any high-risk gate, `applies: false` is invalid unless all of the following are filled: `human_confirmation_required: true`, `confirmed_by`, `confirmed_at`, `reason`, and `evidence`.

## Gate 15 — the Lethal-Trifecta Test

Gate 15 is assessed as a *combination*, not a checklist of independent items. The dominant, adversarially-confirmed 2025 attack against AI-assisted apps (the July 2025 Supabase MCP database-exfiltration incident) succeeds not because any single control is missing, but because three capabilities co-exist in one agent. Ticking "tool permissions scoped" and "RLS on" individually still passes the vulnerable configuration.

**The lethal trifecta** is the co-occurrence, in a single AI agent, MCP server, or LLM tool-chain, of:

1. **Private data** — the agent can read data that is sensitive, another user's, cross-tenant, or production (directly, or through a credential or tool that can).
2. **Untrusted content** — the agent ingests text it did not author and an attacker can influence: support tickets, form submissions, uploaded files, emails, web pages, RAG documents, tool output.
3. **Outbound channel** — the agent can send data or effects outside the trust boundary: replying to the same ticket or email, writing to a shared record, calling an external API, following a URL, emitting a webhook.

When all three are present, prompt injection becomes data exfiltration: instructions hidden in the untrusted content are executed with the agent's privileges, and the results leave through the outbound channel. This is **structural** — an LLM cannot reliably separate instructions from data — so it cannot be patched with better prompts.

**Standard access controls do not break the trifecta.** Row-Level Security does not help when the agent holds a privileged service credential (e.g. Supabase `service_role`), which bypasses RLS entirely. Read-only mode narrows the damage but does not close the trifecta either: it governs database *writes*, whereas the exfiltration path here is *reading* private data, being injected, and sending the result out through the outbound channel — none of which a read-only setting prevents. A reviewer who records "RLS enabled" or "read-only" as the Gate 15 mitigation has recorded false comfort.

**The control is to break a leg** — remove or human-gate any ONE of the three:

- **Private data** — scope the agent's data access to only the requesting user's own data; never give an agent a broad service or admin credential when it also touches untrusted content.
- **Untrusted content** — isolate untrusted text from the tool-calling context (summarize or quote it in a separate, non-privileged step; do not let it reach the model that holds the tools).
- **Outbound channel** — remove it, or require explicit per-action human approval before any tool call that can send data out (the `mcp-ranger` skill governs this at development time).

**Severity.** An AI/agent feature with all three legs and no broken leg is **High** by default. It is **Critical** when a successful injection would expose sensitive, cross-tenant, or production data (the documented incident exfiltrated an entire database, including a table of OAuth/session tokens). Record the three legs and the mitigation in the Gate 15 applicability entry; "RLS on" or "read-only" alone is not an accepted mitigation.

## Severity Model

Use severity to decide whether launch can proceed:

- Critical: blocks launch until the finding is fixed and verified, the affected feature or asset is removed from launch scope, or the severity is downgraded by new evidence. Critical findings cannot be accepted as routine launch risks.
- High: should block launch unless a human owner explicitly accepts the risk with a time-bound mitigation plan.
- Medium: may launch with owner, mitigation, and follow-up date.
- Low: may launch with tracking or documentation.

Critical findings block launch until fixed and verified, removed from launch scope, or downgraded by new evidence.

An exceptional Critical override is not normal approval. If a project defines one, it must require explicit owner approval, documented rationale, compensating controls, and follow-up remediation.

## High-Impact Changes

Treat these areas as high-impact:

- security controls or security assumptions
- authentication, authorization, sessions, identity, or permissions
- privacy, personal data, sensitive data, production data, or retention
- deployment, hosting, domains, networking, secrets, or environment configuration
- database schema, migrations, storage, backups, or destructive data operations
- frontend exposure, client-side tokens, public routes, CORS, CSP, or browser storage
- infrastructure, CI/CD, dependency policy, or supply-chain controls

High-impact changes should update LGF artifacts or explain why no LGF update is needed.

## SDD+ Integration

For each active SDD+ change:

1. Decide whether the change is deployable or high-impact.
2. If LGF applies, update or create the relevant LGF artifacts.
3. Record applied and skipped gates in the change packet.
4. Record decisions, accepted risks, and evidence.
5. Do not mark the change launch-ready if a critical finding remains open.

LGF records are part of durable project memory. Do not rely on chat history for launch-critical decisions.
