# Project Context

## Project Name

Drydock

## Short Description

A working governance framework that makes AI-assisted coding safe enough to
trust. Drydock implements SDD+ — spec-driven development plus a governance and
security layer: governed skills with blocking rules, lifecycle commands,
deterministic safety hooks, independent verification, and the LaunchGuardian
launch-readiness framework with its companion scanner
(`launchguardian-cli`). It currently ships as a Claude Code plugin and is being
planned for a Codex-hosted pilot.

## Audience / Users

Developers building software with AI coding agents ("vibe coders" through
professional engineers) who want their AI-generated changes governed,
verified, and documented. Current shipping platform: Claude Code plugin.
Planned primary orchestration platform: Codex, with Claude/Fable retained as a
cross-model planning and review peer. Any coding agent can already follow the
agent-agnostic project scaffold (`AGENTS.md`, `sdd-plus/`, `scripts/sdd.py`).

## Core Problem

Vibe coding fails in four systemic ways: no source of truth for intended behavior (documentation drift), the AI self-certifies its own work, no deterministic floor under the model's judgment (secrets, destructive git), and ceremony that is either absent or so heavy it kills adoption. Drydock fixes the process, not the model.

## Desired Outcome

Every meaningful AI-assisted change is: specified before implementation (delta specs), governed during implementation (skills + hooks), independently verified (verifier subagent, never the implementer's own report), documented automatically (spec sync at archive), and security-gated before release (LaunchGuardian). All with ceremony proportional to risk (LITE/STANDARD/FULL).

## First Useful Version

Shipped through v0.12.1. The Claude Code plugin is installable from the
marketplace (`danizeap/drydock`), its full lifecycle works end to end, and the
repository records 501 passing tests plus 25 dogfooded change packets.

## Stack And Tools

Preferred:

- Python 3.9+ (stdlib only) for `sdd.py`, hooks, and tooling — no runtime dependencies.
- Markdown for skills, commands, agents, specs, and templates (Claude Code plugin format).
- pytest for the test suite; GitHub Actions for CI.

Avoid:

- Runtime dependencies in shipped scripts/hooks (must run on a bare Python install).
- CLI frameworks — `sdd.py` deliberately reimplements the OpenSpec-inspired lifecycle without a CLI dependency.

## Data And Integrations

- GitHub repo `danizeap/drydock` (MIT), distributed via the Claude Code plugin marketplace.
- Companion scanner: `launchguardian-cli` (separate repo, PyPI: `pip install launchguardian`), orchestrating Gitleaks/Semgrep/Trivy plus native scanners.
- No Drydock telemetry, hosted database, or credential store. Lifecycle and
  policy state stay local; configured Codex/Claude model calls may send guarded
  task or review content through the Owner's provider CLIs.
- Owner runtime plans: Claude Max plus Codex Pro. Fable has a weekly allowance
  that was exhausted in two days during the measured workflow; the Owner
  approved Opus 5 as the current Claude peer fallback, with Fable retained as
  an optional escalation when available.
- Kimi is not part of the current target fleet. `KimiExecutor` remains staged
  historical/reference code and is not evidence of availability.

## Constraints

- **Dual-copy discipline:** files shipped to new projects live twice (root ↔ `assets/project-scaffold/`) and must stay byte-identical; guarded by `scripts/check_sync.py`.
- **Cross-platform:** must work on Windows (`python`), macOS/Linux (`python3`); no bash-isms in shipped tooling.
- **Never overwrite** user files on `/drydock:init-project`.
- **Deterministic enforcement is the product:** hooks and gates must fail closed and be testable; a silent no-op guardrail is worse than none.
- **Preserve in-flight work:** never use `git restore`/checkout-style reversion
  during a packet build. Work may be uncommitted; revert with a deliberate
  inverse edit.
- Assumption (Owner to confirm): solo-maintainer project, no release cadence commitments.

## Design / UX Preferences

Proportional ceremony (framework-theater rule: artifacts only when they change
a decision, preserve understanding, prove behavior, or reduce uncertainty).
Plain-language explanations for Owners. Nautical naming (drydock, seaworthy,
LaunchGuardian).

Flagship models coordinate, make architectural decisions, and cross-review;
right-sized cheaper agents execute bounded typing. The primary task shapes are
bimodal: 1–5 coupled tasks or 12+ mechanical tasks. Avoid handing the
judgment-heavy middle to a cheap model; split it or keep it with a capable
model. The Owner's fuel north star is roughly three useful coding hours as a
pace reserve, not a hard spend budget.

## Definition Of Done

For the current phase (`codex-host-mvp`): Codex can host the full governed
lifecycle without a Claude plugin install; mutating workers are isolated from
the Owner checkout by separate fixed-root workspace-write processes rather than
nested-agent convention; ordinary hook enforcement is described no more
strongly than its tested trust/coverage mechanism; Claude/Fable can participate
through a bounded authenticated peer adapter; verification is isolated in a
separate read-only process and is not mislabeled as cross-model independence;
the existing Claude plugin remains working and compatible.

## Open Questions

- Should a read-only SDD+ MCP server ship so non-Claude agents consume specs/lifecycle over the protocol? (Explored 2026-06; deferred.)
- Remaining sync-gate tiers (MODIFIED/REMOVED/RENAMED semantic verification) — Tier 2 design exists (2026-06 explore session), not yet scheduled.
- What measured burn-rate forecast can honestly protect the Owner's target of
  roughly three useful coding hours without turning it into a hard budget?

## Durable Decisions

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-06-14 | Archive sync gate checks ADDED requirements only (v0.1.3) | Deterministic floor first; MODIFIED/REMOVED/RENAMED need semantic verification (documented limitation) |
| 2026-06-14 | Keep `sdd.py` copies byte-identical; guard with `check_sync.py` | Drift shipped broken behavior to fresh installs before |
| 2026-07-06 | Enforcement layer gets tests + CI before further features | 2026-07 audit: zero tests under a "nothing ships unverified" thesis; bypasses existed because nothing verified the guardrails |
