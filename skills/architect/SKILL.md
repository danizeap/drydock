---
name: architect
description: Plan system architecture before implementation. Use when building a new app, adding a major feature, changing system structure or stack, connecting services, designing agents or database-backed workflows, or making changes that affect architecture, data flow, permissions, deployment, or long-term maintainability. Produces a Build Blueprint before any code is written.
---

# Architect Skill

The anti-chaos skill. Stop coding before you understand what you are building: turn a vague idea into a Build Blueprint another skill can execute. Not required for typos, copy changes, CSS tweaks, renames, or isolated bug fixes — but if a small task reveals architectural uncertainty, pause and switch to this skill before continuing.

## Required inputs

The product idea or change request; intended users and their main jobs; the desired first useful version; known stack/hosting/auth/integration preferences; relevant context from `PROJECT_CONTEXT.md`, specs, standards, or existing code; constraints around private, customer, financial, health, or company data; deadlines, budget, security requirements, non-goals. When key information is missing, make explicit assumptions or mark the result `BLOCKED`.

## Build Blueprint format

```md
# Build Blueprint
1. Product Goal        — what and why
2. Users               — who
3. Core Workflows      — the main things users must do
4. MVP Scope           — first useful version
5. Non-Goals           — intentionally not built yet
6. System Components   — frontend, backend, db, jobs, external services, agents
7. Data Model Sketch   — main entities and relationships
8. Data Flow           — how data enters, moves, transforms, is stored, returned
9. API / Interface Boundaries — what talks to what, and how
10. Auth & Permissions Assumptions — who can do what
11. External Services / Integrations — named, with account/credential/cost dependencies
12. Risks & Tradeoffs  — technical, security, privacy, cost, complexity
13. Implementation Phases
14. Testing Strategy
15. LaunchGuardian Handoff — when release review should happen
16. Next Skill Recommendation
```

## Blocking rules

BLOCK implementation if any of these hold:

- the idea is too vague to plan responsibly;
- data ownership is unclear, or auth/permissions are unclear for sensitive data;
- external services are assumed but not named;
- frontend/backend/database boundaries are unclear;
- there is no MVP boundary or no testing strategy;
- the plan needs secrets/credentials but does not define config handling;
- private, customer, financial, health, or company data is touched without a permission model;
- you cannot explain what should *not* be built yet.

## Boundaries

Do not start implementation before the blueprint exists. Do not invent constraints without labeling them assumptions. Do not bury unresolved architectural questions. Do not choose paid or credentialed external services without naming that dependency. Do not expand scope beyond the first useful version without separating later phases.

## Output

The Build Blueprint, plus a compact evidence note: requirements extracted, key decisions, assumptions, open questions, rejected alternatives, result (`PASS` / `PASS WITH OPEN QUESTIONS` / `BLOCKED`), and the next skill. For meaningful SDD+ work, update durable project files when the blueprint affects lasting architecture, behavior, APIs, data, deployment, or security assumptions.
