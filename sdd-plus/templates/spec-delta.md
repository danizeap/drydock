# Spec Delta: {{CHANGE_NAME}}

Capability: <capability-name>
<!-- Exactly one kebab-case capability per delta file, e.g. user-auth or lead-import. -->


Delta specs describe how this change modifies the living capability spec at
`sdd-plus/specs/capabilities/<capability>.md`. Write requirements as testable
SHALL statements with WHEN/THEN scenarios. A delta represents *intent*, not a
wholesale replacement — include only what changes.

## ADDED Requirements

### Requirement: <name>
The system SHALL <behavior>.

#### Scenario: <name>
- **WHEN** <condition or action>
- **THEN** <observable outcome>

## MODIFIED Requirements

### Requirement: <existing name>
<Only the changes: new/changed scenarios or updated description. Unmentioned
scenarios in the living spec are preserved.>

## REMOVED Requirements

### Requirement: <name to remove entirely>

## RENAMED Requirements

- FROM: `### Requirement: <old name>`
- TO: `### Requirement: <new name>`
