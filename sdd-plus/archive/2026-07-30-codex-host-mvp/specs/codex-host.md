# Spec Delta: codex-host-mvp

Capability: codex-host

## ADDED Requirements

### Requirement: One Codex installation, explicit repository initialization
The system SHALL distribute the Codex host as one Codex plugin installation,
while keeping repository context, SDD+ state, and project-scoped agents as an
explicit per-repository initialization step.

#### Scenario: Plugin installed but repository not initialized
- **WHEN** Drydock is installed in Codex and the active repository lacks
  Drydock project state
- **THEN** readiness reports the plugin as installed and the repository as
  uninitialized, and does not claim that the full SDD+ lifecycle governs it

#### Scenario: Initialized repository
- **WHEN** the Owner initializes a repository
- **THEN** the project receives the agent-agnostic lifecycle state plus the
  Codex-specific project scaffold without requiring a Claude plugin install

### Requirement: Readiness is evidence for this task, not file presence
The Codex host SHALL report plugin version, Codex version, repository
initialization, Python/core discovery, hook source, enabled/trusted/managed
state, active-task liveness, handler revision, covered/uncovered tool paths,
and Claude peer status. It SHALL NOT report a component as live from an
installed file or successful unit probe alone.

#### Scenario: Hooks await trust
- **WHEN** plugin hooks are installed but their current definitions are
  untrusted or modified
- **THEN** readiness reports enforcement inactive and names the trust action
  required

#### Scenario: Existing task predates installation or upgrade
- **WHEN** the active task has no liveness evidence for the current plugin
  revision
- **THEN** readiness reports that a fresh task is required

#### Scenario: Readiness resolves current Desktop task evidence
- **WHEN** Codex exposes the current task identifier to a readiness subprocess
  and exactly one candidate plugin-data root contains both a matching
  SessionStart record and a recent supported Bash `PreToolUse` activity marker
  for the explicit readiness CLI hook-probe flag after deterministic policy
  allowed that command
- **THEN** readiness binds the task identifier, current runtime digest,
  resolved repository root, guarded tool contract, and a system-wall-clock age
  inside the documented freshness and future-skew bounds before it reports
  `current_revision_observed`
- **AND** an absent, malformed, replayed, future-dated, repository-mismatched,
  runtime-mismatched, or ambiguous record is never reported as current-task
  liveness
- **AND** readiness discloses that plugin-data records are unsigned,
  user-writable cooperative evidence rather than proof against a hostile
  agent, that freshness trusts the operating-system wall clock, and that the
  marker may replay inside the documented freshness window

#### Scenario: Thread resumes without current hook activity
- **WHEN** the current thread identifier has a matching record from an earlier
  startup or resume but the readiness invocation is not preceded by a fresh
  supported readiness-probe `PreToolUse` activity marker
- **THEN** readiness reports non-positive liveness and SHALL NOT replay the
  earlier record as `current_revision_observed`

#### Scenario: Hosted and opted-out paths
- **WHEN** readiness describes tool coverage
- **THEN** it explicitly marks hosted tools and specialized opted-out paths as
  uncovered rather than inferring coverage from local-function results

### Requirement: Codex workflows are skills with explicit procedures
The Codex host SHALL expose lifecycle workflows as Codex skills backed by the
authoritative SDD+ procedures and `scripts/sdd.py`. Documentation SHALL call
them skills and SHALL NOT promise Claude slash-command semantics.

#### Scenario: Explicit lifecycle invocation
- **WHEN** the Owner explicitly invokes a Drydock lifecycle skill
- **THEN** the skill follows the same packet gates and evidence rules as the
  corresponding agent-agnostic procedure

#### Scenario: Implicit activation
- **WHEN** Codex selects a Drydock skill from its description
- **THEN** the same deterministic lifecycle CLI and stop conditions apply

### Requirement: The host boundary is adapter-specific
The shared core SHALL contain lifecycle rules, schemas, and only policy
primitives whose contracts are host-neutral and independently tested.
Codex/Claude executable discovery, model names, permission flags, hook
payloads, role labels, and stateful hook orchestration SHALL live in host or
peer adapters. A Claude tool-name dispatcher SHALL NOT be treated as a
host-neutral policy API.

#### Scenario: Existing Claude conductor remains compatible
- **WHEN** the Codex host is added
- **THEN** the working Claude→Codex bridge retains its current behavior and is
  not reclassified as host-neutral shared core

#### Scenario: Existing hook logic is considered for reuse
- **WHEN** an implementation imports behavior from the Claude hook layer
- **THEN** it reuses only proven pure primitives such as secret-path
  classification, shell write-target extraction, and destructive-git token
  analysis; packet, orientation, and completion state machines remain
  adapter-owned

### Requirement: Ordinary Codex hooks have a bounded enforcement claim
User-installed plugin hooks SHALL be described as deterministic local
guardrails only while installed, enabled, current-definition-trusted, loaded
in the active task, and on a supported tool path. Documentation SHALL reserve
non-disableable claims for separately evidenced managed policy.

#### Scenario: User disables hooks
- **WHEN** hooks are disabled globally or individually
- **THEN** readiness reports enforcement inactive and no documentation claims
  the repository is protected by those hooks

#### Scenario: Managed policy is absent
- **WHEN** hooks originate from the ordinary plugin
- **THEN** their profile is `non-managed` and does not use “cannot be reasoned
  around” as an unconditional claim
