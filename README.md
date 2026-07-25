# ⚓ Drydock

**Where vibe code becomes seaworthy.**

Drydock is a free governance framework for AI-assisted development. The
proven Claude Code plugin remains supported, and the additive Codex host MVP
lets Codex pilot the same SDD+ lifecycle while Claude/Opus participates as an
optional architectural peer. A drydock is where a vessel is inspected and
certified before it launches — Drydock is where your AI-generated code lives
before it ships: governed by explicit rules, gated by security checks,
verified independently, and documented automatically.

Vibe coding has a known problem: the code works until it doesn't, and nobody can say what it's supposed to do, whether it's safe, or what changed. Drydock fixes the process, not the model — specs as the source of truth, safety rules that block dangerous moves deterministically, and verification that doesn't take the AI's word for it.

## Install (2 commands)

### Claude Code

```
/plugin marketplace add danizeap/drydock
/plugin install drydock@drydock
```

**Requires Python 3.9+** for the `sdd.py` lifecycle tool — invoked as `python3` on macOS/Linux and `python` on Windows (the `py` launcher also works on Windows).

Using another AI to learn Drydock? Point it at `docs/AI_OPERATOR_GUIDE.md`.

> **Handing this repo to another agent to work on Drydock itself?** Start at **[`docs/HANDOFF.md`](docs/HANDOFF.md)** — the orientation map (what's the brain vs the harness wrapping, what's proven vs assumed, reading order), then **[`docs/CODEX_PORT_PROPOSAL.md`](docs/CODEX_PORT_PROPOSAL.md)** for the in-progress work to re-home Drydock onto Codex.

**Updating:** `/plugin marketplace update drydock`, then `/plugin update drydock@drydock`, then restart. If an update won't take — usually a stale local marketplace clone — see [`docs/DEVELOPING.md`](docs/DEVELOPING.md) for the one-line fix. Maintainers: that file also covers local dev-install and the `scripts/release.py` release flow.

Then, inside any project:

```
/drydock:init-project    # scaffold the structure into your repo
/drydock:onboard         # learn by shipping one small real change (5–10 min)
```

### Codex host MVP

The Codex package is self-contained under `adapters/codex/drydock/`. For a
local development install from this checkout:

```powershell
codex plugin marketplace add .
codex plugin add drydock@drydock
```

Start a fresh Codex task after installation. Review the hook definition and
trust it only if it matches the installed plugin revision, then ask Codex to
“initialize Drydock in this repository.” Initialization is project setup, not
a second host install: Codex previews create-only scaffold writes and waits for
approval before applying them.

Ask Codex to “report Drydock readiness” before relying on enforcement. Ordinary
Codex plugin hooks are hash-trusted, non-managed, user-disableable, and proven
only for canonical local `Bash` and `apply_patch` calls on the tested host.
MCP, hosted, specialized, and other unmatched tool paths remain explicitly
uncovered. Drydock therefore does **not** make a Tier-4 or “cannot be reasoned
around” claim for ordinary Codex plugin hooks.

For governed orchestration, Codex can negotiate with authenticated
`claude-opus-5`, delegate mutation to a separate fixed-root Codex process in a
dedicated worktree, and run a separate read-only verifier. The runner never
merges, commits, pushes, or deploys on the worker’s authority. On the tested
alpha build, Owner config remains part of the child process TCB because it
carries repository trust; the runner reports this and pins integration,
network, rules, environment, hook, and writable-root reductions. Provider,
authentication/base-URL, model-instruction, and unpinned notification or
telemetry settings remain explicit Owner-config trust dependencies. The
runner validates linked-worktree Git control state, snapshots through
temporary Git metadata, directly fingerprints executable Git config/control
bytes before any post-worker Git command, and checks Owner state before
extracting a diff. Git itself is invoked through an absolute executable pinned
before delegation; local config includes and external Git filters are refused
before worktree creation. A kill-on-close Windows Job Object proves descendant
lifetime shutdown before review; filesystem confinement comes from the
separately tested fixed-root sandbox, not from the Job Object itself.
Junctions/reparse points, hardlinks, unsafe link counts, worker-modified Git
attributes, and Git-control drift invalidate review. The mutation-only result
never turns green: it waits for separate verification and deliberate
integration. POSIX process-group cleanup is best-effort and cannot clear a
hostile-descendant gate.
Read-only verifier mode prevents writes but is not claimed to confine reads to
`-C`; its echoed state binding is freshness/anti-replay evidence, not proof of
model observation.

## What you get

**A deterministic safety floor on the paths the active host actually guards.**
Hooks run as code, not polite suggestions the model might ignore. In the
proven Claude host, agent edits to secrets files (`.env`, keys, credentials —
including through shell redirection and PowerShell-native cmdlets like
`Set-Content`) are blocked, and destructive git commands (`push --force`,
`reset --hard`, `clean -f`, stash drops) are stopped before they execute —
across both the Bash and PowerShell shell tools, on macOS, Linux, and Windows.
The Codex host has the narrower, conditional coverage stated above.

**It governs itself.** Three more hooks make the process self-driving, so non-experts stay safe without learning the machinery. Every session **orients itself** — project state, active changes, and a live self-test proving the guardrails still fire — and stays aware of it throughout. Ungoverned edits to narrow high-risk paths (new migrations, CI/CD configs, Dockerfiles) are **caught** with a one-line recovery path, while trivial edits flow free. And "done" is held to mean **verified done**: a change claimed complete with its verification still empty earns one nudge, never a silent pass. Every hook fails toward silence — it can slow a risky move, never break your session.

**It reports to you — in your language.** `/drydock:brief` turns the machinery into a plain-language status: what shipped, what's in flight, what needs you, and what the safety net did lately — each item placed on a fixed **promise ladder** ("being built" → "built, but not yet checked" → "checked & recorded" → "done & documented") captioned with what you can safely say out loud to a customer. Every fact is computed by deterministic code from the project's own records — the model translates, it cannot embellish; anything unreadable says **unavailable** instead of pretending to be fine; a "NOT VERIFIED" record or a forced archive is demoted, never greenwashed. The durable snapshot (`OWNER_STATUS.md`) is machine-authored, self-dating, and guarded against hand-editing — a status surface that would rather admit ignorance than lie to you.

**Twelve governed skills** that load automatically when relevant: backend, frontend, api-contract, database-steward, testing, architect, codebase-cartographer, mcp-ranger (tool-permission governance), explainer, explore-mode, spec-sync, and launchguardian. Each carries explicit blocking rules — a backend change with no auth on a data mutation, a webhook without signature verification, permission logic without negative tests: **BLOCKED**, with the reason stated.

**A spec lifecycle that kills documentation drift.** Changes carry delta specs — testable SHALL requirements with WHEN/THEN scenarios — that merge into living capability specs when the change archives. Archive is gated: verification, spec sync, an API blocking rule (no undocumented API changes ship), then documentation. Your specs stay true because staying true is mechanical.

**Independent verification.** A `verifier` subagent reviews the actual diff in a fresh context: runs the stated tests, maps requirements to implementation evidence (IMPLEMENTED file:line / PARTIAL / NOT FOUND), and refuses to say VERIFIED when a claimed test wasn't run. The implementing agent's report is evidence, not verification.

**Security gates for anything deployable.** The LaunchGuardian Framework defines 22 launch gates (secrets hygiene, API authorization, injection safety, tenant isolation, AI/RAG security, and more) with a hard rule: skipping a high-risk gate requires named human confirmation, and critical findings block launch. The companion scanner, [`launchguardian-cli`](https://github.com/danizeap/launchguardian-cli), validates the records and runs local defensive scans (Gitleaks, Semgrep, Trivy, plus native frontend-exposure and API-surface scanners). Install it with `pip install launchguardian` — optional, everything else works without it.

**Proportional ceremony.** Three execution modes scale rigor to risk: LITE tasks get a four-line summary; FULL tasks (auth, migrations, releases, privileged tools) get full evidence, approval points, and independent review. The framework-theater rule governs everything: an artifact exists only if it changes a decision, preserves understanding, proves behavior, or reduces uncertainty.

## Daily commands

| Command | What it does |
| --- | --- |
| `/drydock:new` | Open a change packet (with delta specs when behavior changes) |
| `/drydock:brief` | Owner brief — plain-language status + `OWNER_STATUS.md` snapshot |
| `/drydock:status` | Active changes, task counts, spec-sync state (engineering view) |
| `/drydock:verify` | Artifacts, spec coverage, independent verifier review |
| `/drydock:sync` | Merge delta specs into living capability specs |
| `/drydock:archive` | Gated close: verify → sync → API rule → docs |
| `/drydock:explore` | Thinking mode — investigate freely, never implement |
| `/drydock:init-standards` | Generate stack-specific standards for this repo |
| `/drydock:init-project` | Scaffold Drydock into a repo |
| `/drydock:onboard` | Guided first change |

## Host model

Claude Code retains auto-loading skills, hooks, the verifier, and slash
commands. Codex now has its own plugin skills, native hook adapter, readiness
reporter, Claude peer adapter, isolated mutation runner, and separate
read-only verifier. The project scaffold (`AGENTS.md`, `sdd-plus/`,
`scripts/sdd.py`) remains agent-agnostic, so both hosts operate the same living
specs and change packets instead of maintaining two governance installations.

## The methodology

Drydock implements **SDD+** — spec-driven development plus a governance and security layer. The full operating protocol lives in `sdd-plus/protocols/framework-usage.md` after init; you don't need to read it to benefit from it.

## Feedback

This is a young, free product. If something blocks you wrongly, triggers when it shouldn't, or costs more than it saves — open an issue. Friction reports are the roadmap.

## Acknowledgements

The delta-spec format, spec-sync concept, archive gating, and explore mode are adapted from the [OpenSpec](https://github.com/Fission-AI/OpenSpec) workflow (MIT) and Jonathan Castro Miguel's OpenSpecs SDD boilerplate (MIT), reimplemented without the CLI dependency. The security layer (LaunchGuardian Framework and CLI), skill governance, execution modes, and enforcement tooling are original to this project.

## License

MIT
