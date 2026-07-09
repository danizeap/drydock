# Brief

## Change

gate15-lethal-trifecta (v0.4.0) — the first LaunchGuardian gate-content upgrade.

Intake: Mode FULL (security-framework change). Primary skill: launchguardian (framework governance); the change is spec/standard/template editing, not code. Approvals: design direction approved by the Owner (2026-07-09, "LaunchGuardian: Gate 15 first"). Evidence base: `sdd-plus/specs/launchguardian-v0.4-gap-research.md` (the CONFIRMED, 3-vote-verified finding). Stop conditions: scope growth into the other v0.4 gate changes (Gate 10 supply-chain, CI/CD, RLS) — those are separate packets; any change to `launchguardian-cli` (that repo is a separate step-zero audit).

## What this means for your product

If an AI agent in your app can read private data, see text from strangers, and send messages out, LaunchGuardian now flags that specific combination as dangerous — because that's the exact setup attackers used to steal whole databases, and it stays dangerous even with your database security switched on.

## User Need

Non-expert builders wire AI agents and MCP servers straight into their database, their email, and their customers' text (support tickets, form submissions, uploaded docs). The single most-documented, adversarially-confirmed attack against this exact stack in 2025 — the "lethal trifecta" Supabase MCP database exfiltration — is not caught by Gate 15 as written. Gate 15 today lists "prompt injection, tool permissions, retrieval boundaries" as separate point-checks, which invites the reviewer to tick "tool permissions: scoped ✓, RLS: on ✓" and pass — while the real risk is the *combination* of three capabilities in one agent, a combination that RLS and read-only mode provably do not neutralize.

## Problem

1. Gate 15's scope is a list of independent items, not the structural combination that actually causes the breach. A reviewer can pass every listed item and still ship the vulnerable configuration.
2. Nothing in the framework names the lethal trifecta (private data + untrusted content + outbound channel) or states that standard access controls (RLS, read-only) do not break it — so a non-expert has no way to know their "secured" setup is the exact vulnerable one.
3. The applicability record has no field to capture the trifecta legs, so even a diligent review leaves no durable evidence that the combination was checked.

## Scope

In scope (each edit in BOTH the root copy and the `assets/project-scaffold/` copy — dual-copy discipline):

1. **`sdd-plus/specs/launchguardian-framework.md`** — expand the Gate 15 table row to name the lethal-trifecta test; add a normative `## Gate 15 — the Lethal-Trifecta Test` subsection: the three legs, the rule (all three in one agent/tool-chain = high-risk regardless of RLS/read-only), the "break a leg" controls, the severity mapping, and the incident citation.
2. **`sdd-plus/security/gate-applicability.template.yml`** and **`gate-applicability.output.template.yml`** — add a recordable `lethal_trifecta` block to the Gate 15 entry (three boolean legs + derived risk + human-confirmation) so the check becomes a durable artifact, not just prose.
3. **`sdd-plus/standards/security-shipping-standards.md`** — one line in Gate Confirmation: an unmitigated trifecta agent is high-risk by default.
4. Delta spec `specs/launchguardian.md` (new `launchguardian` capability) with the ADDED lethal-trifecta requirement; syncs to `sdd-plus/specs/capabilities/launchguardian.md`.

Out of scope:

- The other v0.4 gate changes (Gate 10 supply-chain / install scripts / slopsquatting; CI/CD integrity; Gate 6/16 RLS-on-every-table) — separate evidence-backed packets.
- Any change to `launchguardian-cli` (a separate audit).
- The process improvements (evidence-backed PASS, provenance labels, applicability challenge) — those are their own track.

## Acceptance Criteria

- [ ] Gate 15 names the lethal-trifecta test in the framework spec, with the three legs, the RLS/read-only-don't-fix-it rule, break-a-leg controls, and severity mapping — faithful to the CONFIRMED research finding.
- [ ] The applicability templates carry recordable trifecta legs; a project can capture private-data / untrusted-content / outbound-channel as booleans with a derived risk.
- [ ] Every edited file is byte-identical between its root and `assets/project-scaffold/` copy (verified by diff).
- [ ] `python scripts/check_sync.py` stays green (10/10) and the full pytest suite is unaffected (no code touched).
- [ ] Delta spec written and synced; `sdd.py verify`/`archive` gates pass.
- [ ] Independent verifier confirms the trifecta rule is faithful to the sources and internally consistent, and that no gate name/number drifted across the framework spec, standards, and templates.

## Impact Areas

- Backend: none (no code).
- Frontend: none.
- Data model: none (a new YAML sub-block in the applicability templates).
- API: none.
- AI/model behavior: none in Drydock itself; this governs how AGENTS reviewing a user's project assess AI/agent risk.
- Documentation: the LGF framework spec, security-shipping standards, applicability templates (+ scaffold copies), a new living capability spec.
- Operations/security: this IS a security-framework change — the reason it is FULL mode.

## Open Questions

- None blocking. Deferred by design: whether the trifecta legs should later be auto-detected by the CLI (deps mention openai/anthropic + a DB client + an outbound HTTP/email tool → propose Gate 15 applies with trifecta legs pre-filled). That is a CLI-audit-era enhancement, recorded in the v0.4 roadmap.
