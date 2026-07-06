# Capability: secrets-protection-hook

Capability: secrets-protection-hook

## Purpose

The secrets-path PreToolUse guard (`hooks/protect_secrets.py`). It blocks agent writes to secret-bearing paths on Write/Edit/MultiEdit and on Bash write commands; exit 2 blocks, exit 0 allows. Reads remain allowed.

## Requirements

### Requirement: Secret path coverage
The hook SHALL block Write/Edit/MultiEdit calls whose target path matches a secret-bearing class: `.env` and `.env.*`; `*.env` suffix forms (e.g. `prod.env`); `.envrc`; private keys (`*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `id_ecdsa*`, `id_dsa*`, `*.ppk`); keystores (`*.p12`, `*.pfx`, `*.jks`); `credentials.*`; `secret(s).json/yaml/yml/toml`; and `service-account*.json` / `service_account*.json`. Matching SHALL be case-insensitive and path-separator agnostic.

#### Scenario: Modern SSH key blocked
- **WHEN** a Write targets `~/.ssh/id_ed25519`
- **THEN** the hook exits 2

#### Scenario: Suffix env file blocked
- **WHEN** an Edit targets `config/prod.env`
- **THEN** the hook exits 2

#### Scenario: Keystore blocked
- **WHEN** a Write targets `certs/app.p12`
- **THEN** the hook exits 2

### Requirement: Example files are not secrets
The hook SHALL allow example/template env files: `.env.example`, `.env.template`, `.env.sample` (any directory), consistent with the scaffold `.gitignore` which whitelists `!.env.example`.

#### Scenario: Example env allowed
- **WHEN** a Write targets `.env.example`
- **THEN** the hook exits 0

### Requirement: Bash write coverage
The hook SHALL also run on Bash tool calls and block commands whose first-level write targets match a secret class: output redirections (`>`, `>>`, including attached forms like `>.env`), `tee <path>`, and `cp`/`mv` destinations. Read-only access (e.g. `cat .env`) SHALL remain allowed. Nested shell strings (e.g. `bash -c "..."`) are a documented limitation of this requirement.

#### Scenario: Redirection into .env blocked
- **WHEN** the Bash command is `echo KEY=x > .env`
- **THEN** the hook exits 2

#### Scenario: tee into key blocked
- **WHEN** the Bash command is `cat tmp | tee server.key`
- **THEN** the hook exits 2

#### Scenario: Reading a secret stays allowed
- **WHEN** the Bash command is `cat .env`
- **THEN** the hook exits 0

#### Scenario: Redirection to a normal file stays allowed
- **WHEN** the Bash command is `echo hi > notes.txt`
- **THEN** the hook exits 0
