# Project Context

## Project Name

Drydock

## Short Description

A free Claude Code plugin that makes AI-assisted coding safe enough to trust. Drydock implements SDD+ — spec-driven development plus a governance and security layer: governed skills with blocking rules, lifecycle commands, deterministic safety hooks, an independent verifier subagent, and the LaunchGuardian launch-readiness framework with its companion scanner (`launchguardian-cli`).

## Audience / Users

Developers building software with AI coding agents ("vibe coders" through professional engineers) who want their AI-generated changes governed, verified, and documented. Primary platform: Claude Code (plugin). Secondary: any coding agent, via the agent-agnostic project scaffold (`AGENTS.md`, `sdd-plus/`, `scripts/sdd.py`).

## Core Problem

Vibe coding fails in four systemic ways: no source of truth for intended behavior (documentation drift), the AI self-certifies its own work, no deterministic floor under the model's judgment (secrets, destructive git), and ceremony that is either absent or so heavy it kills adoption. Drydock fixes the process, not the model.

## Desired Outcome

Every meaningful AI-assisted change is: specified before implementation (delta specs), governed during implementation (skills + hooks), independently verified (verifier subagent, never the implementer's own report), documented automatically (spec sync at archive), and security-gated before release (LaunchGuardian). All with ceremony proportional to risk (LITE/STANDARD/FULL).

## First Useful Version

Shipped: v0.1.0 (first public release) through v0.1.4. The plugin is installable from the marketplace (`danizeap/drydock`) and the full lifecycle works end to end.

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
- No user data, no network calls, no telemetry — everything runs locally in the user's repo.

## Constraints

- **Dual-copy discipline:** files shipped to new projects live twice (root ↔ `assets/project-scaffold/`) and must stay byte-identical; guarded by `scripts/check_sync.py`.
- **Cross-platform:** must work on Windows (`python`), macOS/Linux (`python3`); no bash-isms in shipped tooling.
- **Never overwrite** user files on `/drydock:init-project`.
- **Deterministic enforcement is the product:** hooks and gates must fail closed and be testable; a silent no-op guardrail is worse than none.
- Assumption (Owner to confirm): solo-maintainer project, no release cadence commitments.

## Design / UX Preferences

Proportional ceremony (framework-theater rule: artifacts only when they change a decision, preserve understanding, prove behavior, or reduce uncertainty). Plain-language explanations for Owners. Nautical naming (drydock, seaworthy, LaunchGuardian).

## Definition Of Done

For the current phase (v0.1.x hardening): the enforcement layer (hooks + sdd.py gates) has automated tests and CI, the known bypass classes from the 2026-07 six-dimension audit are closed, and Drydock's own repo dogfoods its lifecycle (this file, change packets, living capability specs).

## Open Questions

- Should a read-only SDD+ MCP server ship so non-Claude agents consume specs/lifecycle over the protocol? (Explored 2026-06; deferred.)
- Remaining sync-gate tiers (MODIFIED/REMOVED/RENAMED semantic verification) — Tier 2 design exists (2026-06 explore session), not yet scheduled.

## Durable Decisions

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-06-14 | Archive sync gate checks ADDED requirements only (v0.1.3) | Deterministic floor first; MODIFIED/REMOVED/RENAMED need semantic verification (documented limitation) |
| 2026-06-14 | Keep `sdd.py` copies byte-identical; guard with `check_sync.py` | Drift shipped broken behavior to fresh installs before |
| 2026-07-06 | Enforcement layer gets tests + CI before further features | 2026-07 audit: zero tests under a "nothing ships unverified" thesis; bypasses existed because nothing verified the guardrails |
