# Capability: secrets-protection-hook

Capability: secrets-protection-hook

## Purpose

The secrets-path PreToolUse guard (`hooks/protect_secrets.py`). It blocks agent writes to secret-bearing paths on Write/Edit/MultiEdit and on Bash/PowerShell write commands, DENYING via the PreToolUse JSON `permissionDecision` protocol (exit 0) — never exit 2, which the `python3 X || python X` wrapper swallows. Reads remain allowed. (Scenarios below say "denies"; the block mechanism is the JSON protocol.)

## Requirements

### Requirement: Secret path coverage
The hook SHALL block Write/Edit/MultiEdit calls whose target path matches a secret-bearing class: `.env` and `.env.*`; `*.env` suffix forms (e.g. `prod.env`); `.envrc`; private keys (`*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `id_ecdsa*`, `id_dsa*`, `*.ppk`); keystores (`*.p12`, `*.pfx`, `*.jks`); `credentials.*`; `secret(s).json/yaml/yml/toml`; and `service-account*.json` / `service_account*.json`. Matching SHALL be case-insensitive and path-separator agnostic.

#### Scenario: Modern SSH key blocked
- **WHEN** a Write targets `~/.ssh/id_ed25519`
- **THEN** the hook denies

#### Scenario: Suffix env file blocked
- **WHEN** an Edit targets `config/prod.env`
- **THEN** the hook denies

#### Scenario: Keystore blocked
- **WHEN** a Write targets `certs/app.p12`
- **THEN** the hook denies

### Requirement: Example files are not secrets
The hook SHALL allow example/template env files: `.env.example`, `.env.template`, `.env.sample` (any directory), consistent with the scaffold `.gitignore` which whitelists `!.env.example`.

#### Scenario: Example env allowed
- **WHEN** a Write targets `.env.example`
- **THEN** the hook exits 0

### Requirement: Bash write coverage
The hook SHALL also run on Bash tool calls and block commands whose first-level write targets match a secret class: output redirections (`>`, `>>`, including attached forms like `>.env`), `tee <path>`, and `cp`/`mv` destinations. Read-only access (e.g. `cat .env`) SHALL remain allowed. Nested shell strings (e.g. `bash -c "..."`) are a documented limitation of this requirement.

#### Scenario: Redirection into .env blocked
- **WHEN** the Bash command is `echo KEY=x > .env`
- **THEN** the hook denies

#### Scenario: tee into key blocked
- **WHEN** the Bash command is `cat tmp | tee server.key`
- **THEN** the hook denies

#### Scenario: Reading a secret stays allowed
- **WHEN** the Bash command is `cat .env`
- **THEN** the hook exits 0

#### Scenario: Redirection to a normal file stays allowed
- **WHEN** the Bash command is `echo hi > notes.txt`
- **THEN** the hook exits 0

### Requirement: Denies via the ||-immune JSON protocol, across Bash and PowerShell
The hook SHALL block using the PreToolUse JSON `permissionDecision: deny` protocol on stdout with exit 0 — never exit 2, which the `python3 X || python X` wrapper swallows. Command-based write coverage SHALL apply to the `Bash` AND `PowerShell` shell tools. For PowerShell it SHALL cover native write cmdlets (`Set-Content`, `Out-File`, `Add-Content`, `New-Item`, `Copy-Item`/`Move-Item`/`Rename-Item` destinations, `Tee-Object`, and aliases) in addition to the POSIX forms PowerShell shares. Extraction SHALL be fail-safe: a valueless switch (e.g. `-Verbose`/`-Debug`) before the positional path SHALL NOT hide the path; only known value-parameters skip their value; the destination is the second positional for copy/move/rename; an explicit `-Path` makes later positionals content; `-Path:.env` attached-colon is recognized; and the `.env.example`/template allow-list still allows.

#### Scenario: A PowerShell-native secret write is denied
- **WHEN** `Set-Content -Path .env -Value "K=V"`, `"K=V" | Out-File .env.local`, or `Copy-Item config.json .env` runs through PowerShell
- **THEN** the hook denies

#### Scenario: A valueless switch cannot hide the path
- **WHEN** `Set-Content -Verbose .env "K=V"` runs through PowerShell
- **THEN** the hook denies (the `-Verbose` switch does not consume the path)

#### Scenario: PowerShell content is not a path
- **WHEN** `Set-Content -Path notes.txt -Value credentials.json` runs
- **THEN** the hook allows (credentials.json is content, not a write target)
