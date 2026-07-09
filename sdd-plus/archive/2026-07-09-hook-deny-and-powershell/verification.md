# Verification

## Change

hook-deny-and-powershell

## Automated Checks

- [x] `python -m pytest tests/ -q` — **274 passed, 2 skipped** (was 251; +the fail-open probe test, PowerShell extractor/guard suite, the `||`-chain regression, and the `-Verbose`/`git.exe` fixes).
- [x] `python scripts/check_sync.py` — OK 11/11 (hooks are plugin-only; no scaffold twin).
- [x] **Headline regression, falsification-proven twice:** `tests/test_interpreter_fallback.py` runs the literal `<py> X || <py> X` chain and asserts a JSON deny reaches stdout with exit 0. Reverting either guard to the exit-2 protocol makes it FAIL (deny swallowed, stdout empty) — verified by me and independently by the verifier.
- [x] Fail-open closed (verifier finding #1): `Set-Content -Verbose .env`, `-Debug .env`, `Copy-Item -Verbose config.json .env`, `Add-Content -Verbose .env`, `Out-File -Verbose .env` — all now DENY (were ALLOW). Pinned by `test_valueless_switch_before_path_does_not_hide_it`.
- [x] CI smoke now gates the build (verifier finding #2): `assert_deny` is called directly (not on the right of a pipe), so a failing check exits the step — simulated a non-deny and confirmed exit 1.
- [x] `git.exe reset --hard` detected (verifier finding #3); `mytool.exe status` not flagged; `git status` allowed.

## Manual Checks

- [x] Live smoke: git_safety + protect_secrets deny via JSON exit 0 for Bash AND PowerShell payloads (force-push, `Set-Content .env`); benign commands pass silently.
- [x] No fail-open path: no `return 2` / exit 2 remains in any deny path (grep clean); malformed/non-destructive input still exits 0 (correct fail-open for errors only).
- [x] No false-block: every documented PowerShell trap allows — `-Value credentials.json` (content), `.env.example` (template), positional-after-explicit-`-Path`, `-Path:.env`, unparseable; `command_write_targets(cmd, "Bash")` never runs the PS extractor (tool-faithful).
- [x] Immunity confirmed: completion_gate (Stop, `{"decision":"block"}` exit 0) and packet_guard (JSON exit 0) were already `||`-immune and correctly not changed for bug 1; only packet_guard's PowerShell tool-gate changed.

## Documentation Updates

- [x] README or user-facing docs updated, if needed. (README safety line + operator-guide hook row: JSON-deny protocol, Bash+PowerShell coverage.)
- [x] Project context updated, if needed. (Not needed.)
- [x] Specs updated, if needed. (4 delta specs synced into their living capability specs.)
- [ ] No documentation update needed. Reason: n/a.

## Independent Review

`drydock:verifier`, maximal adversarial mandate (any fail-open OR any realistic false-block = NOT VERIFIED). Two rounds:

1. **Round 1: NOT VERIFIED.** The `||` fix and the false-block side were confirmed clean (the verifier independently reverted to exit-2 and confirmed the regression test bites). But it found a **material fail-open** the reference and its 34 tests missed: a valueless `-Verbose`/`-Debug` switch before the positional path defeated the secrets deny (`Set-Content -Verbose .env` allowed). Plus the CI smoke's assertions were non-fatal (pipe subshell), and `git.exe` bypassed git_safety — both undercutting the packet's own Windows/PowerShell-parity claim.
2. **All three resolved before archive:** the extractor's param default inverted to **fail-safe** (unknown flag consumes nothing — a switch can never hide a path; known value-params still skip their value); CI assertions made build-gating; `git.exe` (and `.exe` git paths) detected. Re-checked: the five fail-open cases DENY, the CI sim exits non-zero, git.exe denies while non-git `.exe` does not, suite 274 green.

## Result

PASS. Two-round adversarial verification: the `||` deny-swallow and PowerShell bypass are fixed and the fixes are falsification-proven; the verifier's round-1 fail-open (which the ported reference itself carried) was closed with a fail-safe redesign, and two faithfulness gaps (non-fatal CI, git.exe) were fixed so the parity claim holds. No fail-open path, no realistic false-block. 274 tests, check_sync 11/11.
