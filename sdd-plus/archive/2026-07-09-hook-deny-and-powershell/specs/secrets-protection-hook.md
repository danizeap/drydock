# Spec Delta: secrets-protection-hook (hook-deny-and-powershell change)

Capability: secrets-protection-hook

## MODIFIED Requirements

### Requirement: Blocks secret-path writes via the ||-immune JSON protocol
The hook SHALL signal a block using the PreToolUse JSON `permissionDecision: deny` protocol on stdout with exit 0 — never exit code 2 (which the `python3 X || python X` wrapper swallows by re-running on drained stdin and failing open). Malformed input and non-secret writes SHALL still result in silent allow with exit 0.

#### Scenario: A secret write survives the interpreter wrapper
- **WHEN** a write to `.env` is evaluated through the actual `python3 X || python X` chain
- **THEN** a JSON deny reaches stdout, the chain exits 0, and the block is not swallowed

### Requirement: Covers PowerShell shell writes, including native cmdlets
The hook SHALL evaluate command-based writes from `tool_name` of `Bash` OR `PowerShell` (and `None`). For PowerShell, the write-target extraction SHALL cover PowerShell-native write cmdlets (`Set-Content`, `Out-File`, `Add-Content`, `New-Item`, `Copy-Item`/`Move-Item`/`Rename-Item` destinations, `Tee-Object`, and aliases) in addition to the POSIX redirection/`tee`/`cp`/`mv` forms PowerShell shares. Extraction SHALL avoid the false-block traps: for copy/move/rename the destination is the second positional; once an explicit `-Path`/`-Destination` binds, later positionals are `-Value` content (never a write target); `-Path:.env` attached-colon form is recognized; unknown `-Param value` pairs skip their value. The documented allow-list (`.env.example`/`.template`/`.sample`) SHALL still allow.

#### Scenario: A PowerShell-native secret write is denied
- **WHEN** `Set-Content -Path .env -Value "K=V"` (or `"K=V" | Out-File .env.local`, or `Copy-Item config.json .env`) is run through PowerShell
- **THEN** it is denied

#### Scenario: Legitimate PowerShell content is not a write target
- **WHEN** `Set-Content -Path notes.txt -Value credentials.json` is run (credentials.json is file CONTENT, not the path)
- **THEN** it is allowed (no false block)
