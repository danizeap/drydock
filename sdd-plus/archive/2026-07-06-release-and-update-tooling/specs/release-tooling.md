# Spec Delta: release-and-update-tooling

Capability: release-tooling

First living spec for `scripts/release.py`, the maintainer release helper that keeps Drydock's version strings in lockstep and gates releases behind the test suite. Dev-only tooling; not shipped in the project scaffold.

## ADDED Requirements

### Requirement: Single lockstep version set
The tool SHALL treat the project version as one value declared in exactly these locations and no others: `.claude-plugin/plugin.json` (`version` key), `.claude-plugin/marketplace.json` (nested plugin `version` key), the `VERSION:` line of `docs/AI_OPERATOR_GUIDE.md`, and a `## <version>` heading in `CHANGELOG.md`. A bump SHALL rewrite each declaring location to the new version and SHALL NOT alter historical version mentions (archived packets, `schema_version`, cache-path strings).

#### Scenario: Bump updates every declaring location
- **WHEN** `release.py 0.1.6` runs against a repo at 0.1.5
- **THEN** plugin.json, marketplace.json, and the operator-guide VERSION line all read 0.1.6 afterward

#### Scenario: Historical mentions are untouched
- **WHEN** a bump runs
- **THEN** version strings inside `sdd-plus/archive/**` and `schema_version` fields are unchanged

### Requirement: Drift detection
Running the tool in check mode (`--check`) SHALL exit 0 when every declaring location agrees and a CHANGELOG entry exists for that version, and SHALL exit non-zero listing the disagreements otherwise. It SHALL make no changes in check mode.

#### Scenario: Disagreement is caught
- **WHEN** `--check` runs while plugin.json says 0.1.5 but the operator-guide VERSION line says 0.1.3
- **THEN** the tool exits non-zero and names both locations and their differing values

#### Scenario: Aligned repo passes
- **WHEN** `--check` runs and all locations agree with a matching CHANGELOG heading
- **THEN** the tool exits 0

### Requirement: Release preflight
A version bump SHALL require the new version to be a valid dotted version strictly greater than the current version, and SHALL require a `## <new-version>` CHANGELOG heading to already exist (the human writes the notes). After rewriting, it SHALL run the test suite and `check_sync.py` and abort with non-zero if either fails.

#### Scenario: Rejects a non-increasing version
- **WHEN** `release.py 0.1.5` runs against a repo already at 0.1.5
- **THEN** it exits non-zero without changing any file

#### Scenario: Rejects a missing changelog entry
- **WHEN** `release.py 0.1.6` runs but CHANGELOG.md has no `## 0.1.6` heading
- **THEN** it exits non-zero telling the maintainer to add release notes first

### Requirement: Prints publish commands, never executes them
The tool SHALL NOT run `git`, network, or history-mutating operations. On a successful bump it SHALL print the exact commit, tag, and push commands for the Owner to run.

#### Scenario: Publish commands are printed, not run
- **WHEN** a bump succeeds
- **THEN** the output contains the `git commit`, `git tag`, and `git push` commands as text, and no git process was invoked by the tool
