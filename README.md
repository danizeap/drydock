# âš“ Drydock

**Where vibe code becomes seaworthy.**

Drydock is a free Claude Code plugin that makes AI-assisted coding safe enough to trust. A drydock is where a vessel is inspected and certified before it launches â€” Drydock is where your AI-generated code lives before it ships: governed by explicit rules, gated by security checks, verified independently, and documented automatically.

Vibe coding has a known problem: the code works until it doesn't, and nobody can say what it's supposed to do, whether it's safe, or what changed. Drydock fixes the process, not the model â€” specs as the source of truth, safety rules that block dangerous moves deterministically, and verification that doesn't take the AI's word for it.

## Install (2 commands)

```
/plugin marketplace add danizeap/drydock
/plugin install drydock@drydock
```

Using another AI to learn Drydock? Point it at `docs/AI_OPERATOR_GUIDE.md`.

Then, inside any project:

```
/drydock:init-project    # scaffold the structure into your repo
/drydock:onboard         # learn by shipping one small real change (5â€“10 min)
```

## What you get

**A safety layer that can't be talked out of.** Hooks block agent edits to secrets files (`.env`, keys, credentials) and stop destructive git commands (`push --force`, `reset --hard`, `clean -f`, stash drops) before they execute â€” deterministic code, not polite suggestions the model might ignore.

**Twelve governed skills** that load automatically when relevant: backend, frontend, api-contract, database-steward, testing, architect, codebase-cartographer, mcp-ranger (tool-permission governance), explainer, explore, spec-sync, and launchguardian. Each carries explicit blocking rules â€” a backend change with no auth on a data mutation, a webhook without signature verification, permission logic without negative tests: **BLOCKED**, with the reason stated.

**A spec lifecycle that kills documentation drift.** Changes carry delta specs â€” testable SHALL requirements with WHEN/THEN scenarios â€” that merge into living capability specs when the change archives. Archive is gated: verification, spec sync, an API blocking rule (no undocumented API changes ship), then documentation. Your specs stay true because staying true is mechanical.

**Independent verification.** A `verifier` subagent reviews the actual diff in a fresh context: runs the stated tests, maps requirements to implementation evidence (IMPLEMENTED file:line / PARTIAL / NOT FOUND), and refuses to say VERIFIED when a claimed test wasn't run. The implementing agent's report is evidence, not verification.

**An escape hatch when work is stuck.** A `mayday` subagent escalates to a premium reasoning model — but only when it's earned it: the same error survived 3+ fix attempts, a FULL-mode architecture call is deadlocked, tests fail systemically across modules, or you call mayday by name. It demands a complete brief, diagnoses the root cause and hands back a numbered plan, and never writes code. Premium cost, so it stays off the routine path.

**Security gates for anything deployable.** The LaunchGuardian Framework defines 22 launch gates (secrets hygiene, API authorization, injection safety, tenant isolation, AI/RAG security, and more) with a hard rule: skipping a high-risk gate requires named human confirmation, and critical findings block launch. The companion scanner, [`launchguardian-cli`](https://github.com/danizeap/launchguardian-cli), validates the records and runs local defensive scans (Gitleaks, Semgrep, Trivy, plus native frontend-exposure and API-surface scanners). Install it with `pip install launchguardian` — optional, everything else works without it.

**Proportional ceremony.** Three execution modes scale rigor to risk: LITE tasks get a four-line summary; FULL tasks (auth, migrations, releases, privileged tools) get full evidence, approval points, and independent review. The framework-theater rule governs everything: an artifact exists only if it changes a decision, preserves understanding, proves behavior, or reduces uncertainty.

## Daily commands

| Command | What it does |
| --- | --- |
| `/drydock:new` | Open a change packet (with delta specs when behavior changes) |
| `/drydock:status` | Active changes, task counts, spec-sync state |
| `/drydock:verify` | Artifacts, spec coverage, independent verifier review |
| `/drydock:sync` | Merge delta specs into living capability specs |
| `/drydock:archive` | Gated close: verify â†’ sync â†’ API rule â†’ docs |
| `/drydock:explore` | Thinking mode â€” investigate freely, never implement |
| `/drydock:init-standards` | Generate stack-specific standards for this repo |
| `/drydock:init-project` | Scaffold Drydock into a repo |
| `/drydock:onboard` | Guided first change |

## Works with other agents too

Claude Code gets the premium experience (auto-loading skills, hooks, the verifier, slash commands). The project scaffold (`AGENTS.md`, `sdd-plus/`, `scripts/sdd.py`) is agent-agnostic â€” Codex and other agents follow the same rules from project files. `/drydock:init-project` offers a portability option that copies the skill definitions into the repo for full non-plugin parity.

## The methodology

Drydock implements **SDD+** â€” spec-driven development plus a governance and security layer. The full operating protocol lives in `sdd-plus/protocols/framework-usage.md` after init; you don't need to read it to benefit from it.

## Feedback

This is a young, free product. If something blocks you wrongly, triggers when it shouldn't, or costs more than it saves â€” open an issue. Friction reports are the roadmap.

## Acknowledgements

The delta-spec format, spec-sync concept, archive gating, and explore mode are adapted from the [OpenSpec](https://github.com/Fission-AI/OpenSpec) workflow (MIT) and Jonathan Castro Miguel's OpenSpecs SDD boilerplate (MIT), reimplemented without the CLI dependency. The security layer (LaunchGuardian Framework and CLI), skill governance, execution modes, and enforcement tooling are original to this project.

## License

MIT
