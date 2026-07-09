# Plan

## Change

hook-deny-and-powershell

## Approach

Deterministic-tier security fix. Build the shared primitives first, migrate the two guards, wire PowerShell, then exhaustively test (porting the reference's proven cases) — testing after each step, because a fail-open regression is invisible without a test that runs the real chain.

1. **`_drydock_common.py`:**
   - `emit_permission_deny(reason)` — prints the PreToolUse JSON deny and flushes; exit stays 0 at the call site. Docstring states the `||`-swallow rationale (exit 2 is forbidden for denies).
   - Port `powershell_write_targets(command)` + tables (`_PS_WRITE_CMDLETS`, `_PS_DEST_CMDLETS`, `_PS_PATH_PARAMS`, `_PS_SWITCH_PARAMS`, `_PS_SEPARATORS`) verbatim from the reference (it is test-proven and handles the false-block traps: destination is the 2nd positional for copy/move/rename; explicit `-Path` binds then later positionals are `-Value` content; `-Path:.env` attached colon; unknown `-Param value` skips its value).
   - `command_write_targets(command, tool_name)` — `bash_write_targets(command)` for Bash; union with `powershell_write_targets(command)` for PowerShell (PS shares POSIX redirection + `cp`/`mv` aliases AND has native cmdlets).
2. **`git_safety.py`:** accept `tool_name == "PowerShell"`; on deny, `emit_permission_deny(block_message(reason))` + `_record_deny` + `return 0` (was stderr + return 2). The existing shlex tokenizer already handles `git reset --hard` in PowerShell (separators `;`/`|`/`&&`/`&` are shared).
3. **`protect_secrets.py`:** accept `tool_name == "PowerShell"` in the command branch; use `command_write_targets(command, tool_name)`; on deny, `emit_permission_deny(...)` + `_record_deny` + `return 0`.
4. **`packet_guard.py`:** accept `tool_name == "PowerShell"` in `classify()`'s command branch; use `command_write_targets(cmd, tool)`. (Already denies via JSON — no protocol change.)
5. **`session_orient.py`:** `probe_guard` parses stdout for a JSON `permissionDecision: deny` whose reason contains the expected fragment (block payload) AND no deny for the benign control, both exit 0 → "live". `_PROBES` `expect` becomes a str fragment ("git-safety guardrail" / "secrets guardrail"). Rationale for keeping the probe single-interpreter: after the migration the deny path exits 0, so `||` never fires — a single-interpreter probe is now representative; the wrapped-chain guarantee is pinned by the pytest below.
6. **`hooks.json`:** matchers `Write|Edit|MultiEdit|Bash` → `…|Bash|PowerShell`; `Bash` → `Bash|PowerShell` (git_safety).
7. **Tests:**
   - Update `test_git_safety.py` / `test_protect_secrets.py`: deny assertions become "stdout carries a JSON deny with the expected reason, exit 0" (helper). Keep all allow cases.
   - Port the reference PowerShell replay cases (git-safety, secrets cmdlets, false-block traps) and the `_ps_write_targets` extractor units.
   - `test_packet_guard.py`: PowerShell high-risk deny (e.g. `Set-Content migrations/x.sql`) + the fixture/soft-segment suppression under PowerShell.
   - New `test_interpreter_fallback.py`: run the literal `python3 X || python X` (and `python X || python X`) chain via subprocess with a destructive-git and a `.env` payload; assert a JSON deny reaches stdout and the chain exits 0 — the regression that proves the `||` gap is closed.
   - `test_session_orient.py`: probe reports "live" on the JSON-deny guards; "degraded" if a guard is swapped for a fail-open stub.
8. **CI + docs:** `ci.yml` smoke — pipe a destructive payload through the guard and assert stdout contains `"permissionDecision": "deny"` (not exit 2); add a PowerShell payload case. Operator guide + README hook rows: deny-via-JSON, PowerShell coverage.

## Files Expected To Change

- `hooks/_drydock_common.py`, `hooks/git_safety.py`, `hooks/protect_secrets.py`, `hooks/packet_guard.py`, `hooks/session_orient.py`, `hooks/hooks.json`
- `tests/test_git_safety.py`, `tests/test_protect_secrets.py`, `tests/test_packet_guard.py`, `tests/test_session_orient.py`, `tests/test_interpreter_fallback.py` (new)
- `.github/workflows/ci.yml`, `docs/AI_OPERATOR_GUIDE.md`, `README.md`, `CHANGELOG.md` (at release)
- Delta specs: `secrets-protection-hook`, `git-safety-hook`, `session-orientation`, `packet-guard`

## Risks

- **Fail-open regression** (the whole reason for the fix). Mitigation: the end-to-end `||`-chain test is the primary gate; every deny path is exercised through the real wrapper.
- **False-block of legitimate PowerShell** (`-Value credentials.json` is content, not a path; `.env.example` is allow-listed). Mitigation: port the reference extractor verbatim (it is built around exactly these traps) and its unit tests.
- **Protocol drift** — a future deny path reverting to exit 2. Mitigation: the shared `emit_permission_deny` helper + its docstring + the chain test.
- **Probe honesty** — a probe that still passes when enforcement is dead. Mitigation: a probe test that swaps in a fail-open stub and asserts "degraded".

## Rollback

Every change is additive or a localized protocol swap. Reverting the six hook files restores the prior behavior (the old exit-2 deny — which is the buggy state, so rollback is only for emergencies). No data, no migration. `git revert` of the release commit is clean. The hooks are plugin-only, so nothing ships into user projects until they update the plugin.
