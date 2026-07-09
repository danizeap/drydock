# Spec Delta: git-safety-hook (hook-deny-and-powershell change)

Capability: git-safety-hook

## MODIFIED Requirements

### Requirement: Blocks destructive git via the ||-immune JSON protocol
The hook SHALL signal a block using the PreToolUse JSON `permissionDecision: deny` protocol on stdout and exit 0 — NOT exit code 2. Exit code 2 is forbidden for denies because `hooks.json` wraps every hook as `python3 X || python X`: a non-zero exit is read by the shell as launch failure, re-runs the hook on already-drained stdin, and fails open, silently losing the deny on any machine where `python3` works. The block reason (the destructive-operation explanation) SHALL travel in `permissionDecisionReason`. Any error, malformed input, or non-destructive command SHALL still result in silent allow with exit 0.

#### Scenario: A destructive command is denied and survives the interpreter wrapper
- **WHEN** a destructive git command is evaluated through the actual `python3 X || python X` chain
- **THEN** a JSON `permissionDecision: deny` reaches stdout, the chain exits 0, and the block is not swallowed

### Requirement: Covers the PowerShell shell tool
The hook SHALL evaluate commands from `tool_name` of `Bash` OR `PowerShell` (and the unlabeled/`None` case), since the Windows harness exposes a separate PowerShell tool that can run the same destructive git commands. Its token-based parsing already handles PowerShell command strings (shared separators `;`/`|`/`&&`/`&`, the call operator, and identical `git` invocation).

#### Scenario: Destructive git via PowerShell is denied
- **WHEN** `git reset --hard` (or a force/mirror/delete push) is run through the PowerShell tool
- **THEN** it is denied, identically to the Bash tool
