# Decision Log

## Change

codex-enforcement-bridge

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-23 | Reuse the plugin guards via a thin dispatcher, not re-implement the logic | The plugin guards (secret patterns, git tokenizer, PowerShell extractor, JSON protocol) are the tested single source of truth; re-deriving them for Codex invites drift and a second fail-open surface | A fully self-contained re-implementation in `.codex/` (rejected for v1: duplicates ~600 lines of security logic and its false-block traps); generate a bundle from the plugin at release (deferred — a fast-follow for plugin-less Codex users) |
| 2026-07-23 | The bridge is mostly wiring because Codex speaks the SAME `permissionDecision: deny` protocol | The Codex audit confirmed `.codex/hooks.json` uses the identical PreToolUse deny protocol; the v0.5.0 JSON-deny migration is exactly what makes the guards portable | Building a Codex-specific protocol adapter (unnecessary — protocols match) |
| 2026-07-23 | Fail OPEN when the plugin can't be resolved or on any error | A guardrail bug must never brick a Codex session (Drydock's universal hook contract); the git pre-commit hook remains an agent-agnostic backstop for the secrets class | Fail closed / block when unresolvable (rejected: bricks pure-Codex sessions; violates the fail-open contract) |
| 2026-07-23 | Use Codex's `command` + `commandWindows` split, not `python3 X \|\| python X` | Codex's hooks.json supports a Windows-specific command variant — a cleaner cross-platform answer than the `||` fallback (which caused the v0.5.0 deny-swallow); no swallow risk | Reuse the `python3 \|\| python` pattern (rejected: Codex gives a better native mechanism, and `||` was the exact v0.5.0 bug) |
| 2026-07-23 | v1 covers the STATELESS guards (secrets + destructive-git); defer packet_guard | Secrets + destructive-git are the critical "can't be talked out of" floor and are stateless (no session/ledger state to port); packet_guard needs project state and the warn tier — a larger, separate port | Port everything including packet_guard now (rejected: stateful, larger surface, not the critical floor) |
| 2026-07-23 | Add an agent-agnostic git pre-commit secrets hook alongside the Codex PreToolUse bridge | A git hook fires for Codex, Claude Code, AND a human commit — the universal backstop that holds even if a tool's hook layer is disabled or bypassed (Codex hooks can be turned off unless admin-pinned) | Rely only on each tool's PreToolUse hooks (rejected: leaves the human-commit path and disabled-hook case unguarded) |
