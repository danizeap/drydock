# Capability: packet-guard

Capability: packet-guard

## Purpose

`hooks/packet_guard.py`, the PreToolUse guard that catches ungoverned work — edits in a Drydock project when no change packet is active. Risk-tiered (silent / warn-once / narrow deny); the fail direction is silent-allow (a wrongful deny is the worst outcome); always exits 0; never emits `updatedInput`.

## Requirements

### Requirement: Silent for governed and legitimate-LITE work
The guard SHALL emit nothing when: the session is not in a Drydock project; the target path is outside the project (including scratch/temp files, with a target-anchored discovery fallback so a session parked outside the project still governs writes INTO one); an active packet exists (any `sdd-plus/changes/` subdirectory carrying a `tasks.md`, kebab-named or not — bare directories without artifacts do not count); or the path is exempt — `sdd-plus/**`, `.claude/**` except `settings*.json`, documentation files (`*.md` and friends), licenses and git metadata. Exemption SHALL take precedence over the deny tier (docs inside a migrations directory are docs).

#### Scenario: Packet active silences everything
- **WHEN** any packet with a tasks.md exists and a high-risk path is edited
- **THEN** the guard emits nothing

#### Scenario: Non-kebab packet still counts
- **WHEN** the only packet directory is named `Fix_CI` with a tasks.md
- **THEN** source edits are silent (no wrongful "no packet" verdict)

#### Scenario: Sibling repo sharing a path prefix is outside
- **WHEN** the project is `.../drydock` and the edit targets `.../drydock-experiments/auth/handler.py`
- **THEN** the guard emits nothing (containment is path-aware, not string-prefix)

#### Scenario: Docs in a high-risk directory are exempt
- **WHEN** `migrations/README.md` is edited with no packet
- **THEN** the guard emits nothing

### Requirement: Warn once per session on ungoverned source edits
For an in-project, non-exempt Write/Edit/MultiEdit with no active packet and no high-risk match, the guard SHALL allow the edit and attach a single per-session orientation note (via `additionalContext`) that blesses trivial LITE work and points meaningful work at `/drydock:new`. The warned flag SHALL be persisted (copy-and-update on the shared session-state file) BEFORE the note is emitted; if persistence is unavailable or fails, the guard SHALL stay silent rather than re-warn. Bash writes SHALL NOT trigger the warn tier. The warn is orientation, not enforcement.

#### Scenario: One warn, then silence
- **WHEN** two ungoverned source edits happen in one session
- **THEN** only the first carries the note

#### Scenario: State channel unavailable degrades to silence
- **WHEN** the session-state file cannot be read or written
- **THEN** no note is emitted and the edit proceeds

### Requirement: Deny narrow high-risk work without a packet
With no active packet, the guard SHALL deny (permissionDecision `deny`, fixed-template reason naming the recovery: create a packet and retry) only for: schema-migration paths (a `migrations` segment, or ADJACENT `db`+`migrate` segments); CREATION of new CI config (`.github/workflows/**`, `.gitlab-ci.yml`, `Jenkinsfile`) — edits to existing CI files only warn; and container build/deploy configs (`Dockerfile` and `Dockerfile.*` exact-name family, `docker-compose.*`, `compose.yml/yaml`). Matching SHALL be lexical on the normalized, casefolded, **project-relative** path — directory segments above the project root SHALL never classify (a project living under a folder named `migrations` is not itself a migration). A test/fixture/example/docs path segment SHALL suppress the deny. The same deny classes SHALL apply to Bash AND PowerShell first-level write targets (POSIX redirections, tee, cp/mv destinations, and PowerShell-native write cmdlets, via the extraction logic shared with the secrets guard), so the deny tier cannot be escaped by switching shells. A `>` quoted inside a larger shell argument (grep patterns, commit messages) SHALL NOT be treated as a redirection. Known limitation (documented, accepted): a quoted argument consisting of redirect-shaped text alone (e.g. `grep ">" file`) is indistinguishable from the operator after tokenization and may still match.

#### Scenario: Ungoverned migration is denied with a recovery path
- **WHEN** `migrations/0002_add_users.sql` is written with no packet
- **THEN** the write is denied and the reason names packet creation as the retry path

#### Scenario: Tests near high-risk names are not denied
- **WHEN** `tests/migrations/test_0001.py` or `src/auth/login.tsx` is edited with no packet
- **THEN** the guard warns at most (never denies)

#### Scenario: Editing an existing workflow is routine
- **WHEN** an existing `.github/workflows/ci.yml` is edited with no packet
- **THEN** the guard warns at most; creating a NEW workflow file is denied

#### Scenario: Shell redirection cannot dodge the deny tier
- **WHEN** the Bash command `echo "ALTER TABLE x" > migrations/0003.sql` runs with no packet
- **THEN** the command is denied

#### Scenario: Ancestor directories never classify
- **WHEN** the project itself lives at `.../migrations/projC/` and `src/app.py` is edited with no packet
- **THEN** the guard warns at most (never denies)

#### Scenario: Quoted mentions of redirections are not writes
- **WHEN** the Bash command is `git commit -m "deny writes > migrations/0001.sql"`
- **THEN** the guard emits nothing

### Requirement: Generated status file is deny-protected
The guard SHALL deny Write/Edit/MultiEdit calls and Bash first-level write targets whose basename casefolds to `owner_status.md` within a Drydock project — regardless of packet state, since the file is a generated artifact whose hand-editing is never governed work — with a fixed-template reason naming the recovery path (`/drydock:brief` regenerates it). The engine's own `--write-status` path is script-internal I/O and is unaffected. Test/fixture/example/docs-directory path segments SHALL suppress this deny like every other deny class. This deny SHALL append a distinct ledger category and SHALL follow the guard's universal contracts (silent-allow on any error, never `updatedInput`).

#### Scenario: Freelance green status is stopped
- **WHEN** an agent writes OWNER_STATUS.md directly, with or without an active packet
- **THEN** the write is denied and the reason points at /drydock:brief

#### Scenario: Fixtures stay editable
- **WHEN** tests/fixtures/OWNER_STATUS.md is edited
- **THEN** the guard does not deny

### Requirement: Never breaks an edit
Any error, malformed input, unknown tool payload shape, or untrusted cwd/session id SHALL result in silent allow with exit 0. Out of scope by design (stated, not hidden): NotebookEdit and MCP write tools (mcp-ranger governs privileged tools), Bash for the warn tier, per-edit packet attribution, and bare quoted-`">"` tokens.

#### Scenario: Garbage stdin never blocks
- **WHEN** stdin is empty, non-JSON, or missing fields
- **THEN** the guard exits 0 with no output
