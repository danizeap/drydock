# Tasks

## Change

hook-deny-and-powershell

## Implementation

- [x] Write delta specs (secrets-protection-hook, git-safety-hook, session-orientation, packet-guard) — before implementing.
- [x] `_drydock_common.py`: `emit_permission_deny()`; ported `powershell_write_targets()` + tables; `command_write_targets(command, tool_name)`.
- [x] Migrated `git_safety.py` to JSON deny + accept PowerShell (+ docstring).
- [x] Migrated `protect_secrets.py` to JSON deny + accept PowerShell + `command_write_targets` (+ docstring).
- [x] `packet_guard.py`: accept PowerShell + `command_write_targets`.
- [x] `session_orient.py`: probe detects JSON deny; `_PROBES` expect fragments (str); + fail-open probe test.
- [x] `hooks.json`: PowerShell added to the three PreToolUse matchers.
- [x] Updated the exit-2 deny assertions (event-ledger verdict test, session_orient probe) to the JSON protocol; ported PowerShell replay + extractor-unit tests (`test_powershell_targets.py`); PowerShell packet_guard deny + fixture suppression.
- [x] New `test_interpreter_fallback.py`: the real `python3 X || python X` chain preserves a destructive deny — falsification-proven (reverting to exit-2 fails it).
- [x] Full pytest 271 passed / 2 skipped; live-smoked PowerShell destructive payloads (git force-push, Set-Content .env) → JSON deny, exit 0.
- [x] CI smoke rewritten (JSON deny + PowerShell + `||`-chain) + operator-guide/README hook descriptions.
- [x] Sync delta specs (4 living capability specs updated to JSON-deny + PowerShell); verifier subagent — round 1 NOT VERIFIED (real `-Verbose` fail-open + non-fatal CI + git.exe), all three fixed and re-verified; `sdd.py verify` passes.
