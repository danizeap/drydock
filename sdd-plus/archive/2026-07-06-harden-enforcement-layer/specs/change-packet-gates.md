# Spec Delta: harden-enforcement-layer

Capability: change-packet-gates

First living spec for the deterministic packet gates in `scripts/sdd.py` (verify and archive).

## ADDED Requirements

### Requirement: Placeholder gate catches shipped template forms
`verify` SHALL flag as unfilled any required artifact containing template placeholder residue in the forms the shipped templates actually use: whole-line `TBD` (with or without a list dash), checkbox `- [ ] TBD`, table-cell `| TBD |`, unreplaced `{{CHANGE_NAME}}`, and a verification.md whose `## Result` section still reads `Pending.`

#### Scenario: Pristine template packet fails verify
- **WHEN** `verify` runs on a packet whose verification.md and decision-log.md are untouched from the shipped templates
- **THEN** the exit code is 1 and the warning names those files

#### Scenario: Genuinely filled packet passes
- **WHEN** all required artifacts have real content and a non-Pending Result
- **THEN** `verify` exits 0 with no placeholder warning

### Requirement: Archive fails closed on unattributable delta specs
WHEN a delta spec file under the change's `specs/` directory yields no valid kebab-case capability (missing `Capability:` line, placeholder value, or non-kebab value), `archive` SHALL exit with an error naming the file instead of silently skipping the sync gate; `--force` remains the explicit override.

#### Scenario: Placeholder capability line blocks archive
- **WHEN** a delta file's capability line is still `Capability: <kebab-capability-name, e.g. user-auth, lead-import>`
- **THEN** `archive` (without --force) exits non-zero naming that file

### Requirement: Exact requirement-name matching in the sync gate
The archive sync gate SHALL treat a delta's ADDED requirement as synced only when a living-spec heading's requirement name equals the delta's requirement name after whitespace/case normalization — substring containment SHALL NOT count.

#### Scenario: Substring no longer false-passes
- **WHEN** the delta adds `Session` and the living spec contains only `### Requirement: Session Expiry`
- **THEN** the gate reports `Session` as not synced

### Requirement: ADDED-section parsing respects section boundaries
The ADDED-requirement parser SHALL stop collecting at the next `##` heading of any kind, SHALL ignore fenced code blocks, and capability extraction SHALL do the same.

#### Scenario: Requirements under a Notes section are not ADDED
- **WHEN** a delta has `## ADDED Requirements` with one requirement followed by `## Notes` containing `### Requirement: Example`
- **THEN** only the first requirement is treated as ADDED

#### Scenario: Fenced capability lines are ignored
- **WHEN** a delta's only `capability:` text appears inside a fenced code block
- **THEN** the file yields no capability (and archive fails closed per the unattributable rule)
