# Brief

## Change

hook-deny-and-powershell (v0.5.0) — close two live-fire-confirmed enforcement holes in the deny path.

Intake: Mode FULL (deterministic-enforcement tier — the highest rigor; a wrong fix fails open or false-blocks the Owner's real work). Primary skill: backend. Approvals: Owner reported both gaps from a live-fire audit of a governed project (2026-07-09) and directed the fix. Reference implementation to port: `secpho_intelligence_system/.claude/hooks/drydock_deny_guards.py` (`_ps_write_targets`) + 34 replay tests. Stop conditions: any change that makes a guard fail open on a real destructive/secret write; any false-block of legitimate PowerShell content (the `-Value credentials.json` trap); scope growth beyond the deny path.

## What this means for your product

Two ways the safety net was silently letting dangerous commands through — one on every machine where `python3` works, one for every command run through PowerShell on Windows — are now closed, so "the guards can't be talked out of" is true in practice, not just on paper.

## User Need

The guardrails are the product's deepest promise: deterministic blocks that "can't be reasoned around." A live-fire audit proved two ways that promise was broken in the shipped plugin — both failing OPEN (no enforcement), the worst direction:

1. **The interpreter fallback swallows denies (severe, all-machines).** `hooks.json` wires every hook as `python3 X || python X`. `git_safety.py` and `protect_secrets.py` deny via **exit code 2**. The shell's `||` reads a non-zero exit as *launch failure* and re-runs the script on already-drained stdin; the second run reads empty input, fails open (exit 0), and the chain's overall exit is 0 — **the deny is silently lost on any machine where `python3` works.** Live-fire probes confirmed real destructive-git and `.env` writes went through while the scripts' own verdicts were being journaled to the event ledger. `packet_guard` and `completion_gate` are immune because they emit their block via the JSON protocol with **exit 0**.
2. **PowerShell bypasses every guard on Windows.** The harness exposes a separate PowerShell tool; the guards hard-gate on `tool_name == "Bash"`, so any destructive command run through PowerShell is unguarded. And even if the tool gate were opened, `bash_write_targets()` only understands POSIX redirection/`tee`/`cp`/`mv` — it misses PowerShell-native writes (`Set-Content`, `Out-File`, `Add-Content`, `New-Item`, `Copy-Item`/`Move-Item`/`Rename-Item` destinations).

## Problem

- Exit-2 as a deny signal is fundamentally incompatible with the `python3 || python` wrapper the plugin needs for cross-platform interpreter resolution.
- The SessionStart liveness probe reports "git-safety live; secrets live" by testing the scripts under one interpreter and checking for exit 2 — so it **overstates enforcement**: it says "live" while the wrapped chain fails open.
- The whole guard layer assumes Bash is the only shell.

## Scope

In scope (hooks are plugin-only — no scaffold twin, no dual-copy):

1. **Migrate `git_safety.py` and `protect_secrets.py` to the JSON `permissionDecision: deny` protocol (exit 0)** — the `||`-immune protocol `packet_guard` already uses. Add a shared `emit_permission_deny()` to `_drydock_common` documenting *why* exit 2 is forbidden.
2. **Fix the SessionStart liveness probe** (`session_orient.py`) to detect a JSON deny on stdout instead of exit 2, so "live" means what it says.
3. **PowerShell coverage:** (a) add `PowerShell` to the three PreToolUse matchers in `hooks.json`; (b) accept `tool_name == "PowerShell"` in `git_safety`, `protect_secrets`, and `packet_guard`'s command branches; (c) port `powershell_write_targets()` (+ the cmdlet/param tables) into `_drydock_common` and add `command_write_targets(command, tool_name)` that unions POSIX + (for PowerShell) native-cmdlet targets — natively, NOT the reference's relabel-to-Bash hack.
4. **Tests:** update the exit-2 deny assertions to the JSON protocol; port the reference's PowerShell replay + extractor-unit tests; add an end-to-end regression that runs the actual `python3 X || python X` chain and asserts a destructive deny survives.
5. **CI + docs:** update the guardrail smoke steps (exit 2 → JSON deny) and the operator-guide/README hook descriptions.

Out of scope:

- Any shell beyond Bash and PowerShell (cmd.exe, etc.).
- NotebookEdit / MCP write tools (mcp-ranger's domain).
- The Owner's project-level dispatcher (theirs to remove once this ships).

## Acceptance Criteria

- [ ] `git_safety` and `protect_secrets` deny via JSON + exit 0; the `python3 X || python X` chain preserves a destructive-git deny and a `.env`-write deny end-to-end (pinned by a real subprocess-chain test).
- [ ] The liveness probe reports "live" only on a genuine JSON deny + benign allow; it does not report "live" if a guard fails open.
- [ ] PowerShell destructive git and PowerShell-native secret writes (`Set-Content`/`Out-File`/`Copy-Item` dest/…) are denied; the false-block traps (`-Value credentials.json`, `.env.example`, positional-after-explicit-path, `-Path:.env`) do NOT deny — the reference's 34 cases pass.
- [ ] Bash behavior is unchanged (all existing git/secrets/packet-guard tests pass, updated only for the JSON protocol).
- [ ] Full suite green; verifier confirms no fail-open path and no false-block, adversarially.

## Impact Areas

- Backend: `hooks/*.py`, `hooks/_drydock_common.py`, `hooks/hooks.json`.
- Operations/security: THIS IS the security enforcement layer — FULL mode.
- Documentation: operator guide + README hook descriptions; `.github/workflows/ci.yml` smoke.

## Open Questions

- None blocking. Deferred: a PowerShell payload in the runtime liveness probe (the test suite covers PowerShell; adding a PS probe to every session start is optional polish).
