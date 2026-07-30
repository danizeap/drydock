# Capability: codex-plugin-enforcement

Capability: codex-plugin-enforcement

## Purpose

The Codex plugin enforcement capability: Codex-native hook contracts, definition-bound runtime integrity, fail-closed supported calls, honest readiness, and separate repository initialization.

## Requirements

### Requirement: Codex plugin guards use Codex contracts
The Codex plugin SHALL bundle its hook definitions and Codex adapter separately
from the existing legacy project-scaffold bridge. The adapter SHALL reuse only
proven host-neutral policy primitives while consuming canonical Codex tool
names and inputs, including `Bash`, `apply_patch`, MCP names, and relevant
local function tools. It SHALL NOT call the Claude-name dispatcher
`protect_secrets.check()` as a shared policy API. It SHALL provide
Windows-specific commands and emit Codex-supported structured deny output.
Security hook definitions SHALL use narrow, explicit matchers for the supported
side-effect tool contracts. They SHALL NOT register one broad fail-closed
matcher across unrelated or read-only tools.

#### Scenario: Native apply_patch secret creation denied
- **WHEN** Codex reports canonical `tool_name: "apply_patch"` with a patch that
  creates or modifies a secret-bearing file
- **THEN** the plugin hook denies the tool before execution

#### Scenario: PowerShell command arrives as Bash
- **WHEN** Codex executes a PowerShell command through its local shell path
- **THEN** the adapter evaluates it under canonical tool name `Bash`

#### Scenario: MCP and other local functions
- **WHEN** a supported MCP or local function tool enters the hook path
- **THEN** the adapter receives its canonical name and applies only policies
  whose argument contract is understood; unknown side-effect contracts are
  denied rather than guessed

#### Scenario: Unknown or unmapped tool name
- **WHEN** a guarded hook receives a tool name that is not in the explicit
  side-effect contract expected by that matcher
- **THEN** the adapter emits a structured deny and reports the tool contract as
  unsupported

#### Scenario: Tool does not match a guarded contract
- **WHEN** a read-only, renamed, or otherwise unmatched tool is outside every
  explicit guarded matcher
- **THEN** that hook is not invoked for the call, readiness reports the tool as
  uncovered, and Drydock does not claim it was allowed by policy

#### Scenario: Stateful lifecycle hook runs
- **WHEN** packet, session-orientation, or completion behavior is evaluated
- **THEN** the Codex adapter uses a Codex-native state machine conforming to the
  shared lifecycle contract rather than treating the Claude hook entry point
  as a pure function

#### Scenario: Windows plugin cache path contains spaces
- **WHEN** the plugin is installed under a Windows path containing spaces
- **THEN** `commandWindows`, `PLUGIN_ROOT`, and `PLUGIN_DATA` resolve and the
  handler executes successfully

### Requirement: Trusted definitions verify every mutable executable before use
The build SHALL produce one self-contained, plain UTF-8 Python runtime file
with LF line endings, no BOM, no timestamps or archive metadata, a fixed header,
and source sections in a declared deterministic order. Zip/pyz output SHALL NOT
be used for this bundle. It SHALL compute a canonical SHA-256 digest over the
exact runtime bytes and explicit file manifest. Every security-relevant hook
command SHALL contain both the expected digest and the complete minimal
verifier program literally inside the trusted hook definition (or invoke an
equivalently immutable platform-managed verifier). The verifier
SHALL open and read each manifested runtime file once, validate the manifest
and digest over those captured bytes, run under isolated/no-site interpreter
startup, pin module search paths to trusted standard-library roots away from
the repository and mutable plugin directories, and compile/execute the
already-verified bytes in memory. It SHALL NOT verify a path and then import or
execute a second read of that path. A mismatch, unexpected importable runtime
file, attempted mutable plugin import, or failure to establish the isolated
import boundary SHALL deny the supported tool call.

CI SHALL deterministically rebuild the runtime bundle from its declared source
inputs into a temporary path and compare exact bytes with the committed bundle
and embedded digest on every change, alongside `check_sync.py`. Release
verification SHALL repeat the same check. A stale bundle that omits a
source-policy change SHALL fail CI and release verification.

#### Scenario: Handler content changes without a definition update
- **WHEN** any manifested executable or policy byte changes while the trusted
  definition retains the prior digest
- **THEN** the definition-bound verifier denies the supported tool call before
  executing the changed bytes, and release verification fails

#### Scenario: Mutable runtime bundle is tampered
- **WHEN** the external runtime bundle is modified to skip or weaken policy
  checks
- **THEN** the definition-bound verifier detects its changed bytes and denies
  the call before those bytes execute

#### Scenario: Definition-bound verifier is modified
- **WHEN** the inline verifier program or expected digest in the hook command is
  changed
- **THEN** the hook definition hash changes and Codex requires a new trust
  review before it can run

#### Scenario: Arbitrary revision changes with handler content
- **WHEN** handler content changes and a developer substitutes an arbitrary
  revision string rather than the recomputed canonical digest
- **THEN** CI and release verification recompute the bundle, detect the
  mismatch, and fail

#### Scenario: Policy source changes but bundle is stale
- **WHEN** a declared pure-policy source changes without regenerating the
  self-contained runtime bundle
- **THEN** deterministic rebuild comparison fails CI before merge and fails
  release verification

#### Scenario: Bundle is rebuilt twice
- **WHEN** the same declared sources are bundled twice on the same or different
  supported platforms
- **THEN** the normalized plain-source outputs are byte-identical and have the
  same SHA-256 digest

#### Scenario: Manifest omits or gains executable code
- **WHEN** an imported handler/policy file is omitted from the manifest or an
  unexpected executable hook file appears
- **THEN** runtime verification denies and release verification fails rather
  than producing a partial digest

#### Scenario: File changes after verification
- **WHEN** the on-disk runtime file is replaced after its bytes have been read
  and verified but before policy evaluation
- **THEN** the current invocation executes only the captured verified bytes and
  never re-reads or imports the replacement

#### Scenario: Runtime attempts a plugin-local import
- **WHEN** verified runtime code attempts to import executable code from a
  mutable plugin directory
- **THEN** the pinned import boundary rejects it and the guarded call is denied

#### Scenario: Repository contains Python startup injection
- **WHEN** the working directory contains `sitecustomize.py`, `usercustomize.py`,
  or another import-shadow candidate
- **THEN** isolated/no-site interpreter startup and the pinned import path
  prevent that repository code from executing before or during the guard

#### Scenario: Exact bundle digest changes
- **WHEN** the canonical handler bundle legitimately changes and its exact
  digest is embedded in the definitions
- **THEN** Codex observes changed hook definitions and requires a new trust
  review

#### Scenario: Windows command path and length are exercised
- **WHEN** release verification runs on Windows from a plugin path containing
  spaces
- **THEN** the exact inline verifier command succeeds through the supported
  launcher, remains below the proven command-line limit, and executes the
  verified in-memory bundle

### Requirement: Running security handlers fail closed on supported calls
After the definition-bound verifier transfers control to the verified in-memory
runtime, malformed payloads and
secret/destructive-git/governed-high-risk policy exceptions SHALL emit a
concrete Codex deny result before tool execution. An internal error SHALL NOT
return allow or a non-blocking “unavailable” result for the current supported
tool call.

#### Scenario: Guard raises internally
- **WHEN** a security policy raises while evaluating a supported tool call
- **THEN** the adapter emits a generic structured deny, records only a
  non-secret failure category, and the tool action does not run

#### Scenario: Payload is malformed
- **WHEN** the running handler cannot validate the payload for a supported
  guarded tool
- **THEN** it denies the tool and a negative test proves the requested side
  effect did not occur

### Requirement: Hook-start failures invalidate readiness
If Python, the definition-bound verifier, or the hook command cannot start far
enough to return a policy decision, Drydock SHALL treat enforcement as inactive
for the active task. Readiness and documentation SHALL NOT claim the guard ran
or blocked the current call.

#### Scenario: Python or inline verifier cannot start
- **WHEN** Codex reports hook execution failure before a policy decision
- **THEN** active-task readiness is invalid, the failure is surfaced, and no
  positive enforcement result is recorded

#### Scenario: Trusted computing base is reported
- **WHEN** readiness describes handler integrity
- **THEN** it names the Codex host, operating system, selected interpreter,
  hook definition, and trust store as assumptions and does not claim that the
  ordinary plugin cryptographically attests those components

### Requirement: Plugin wiring and project initialization are separate
The Codex plugin installation SHALL provide plugin-level hook wiring.
Repository initialization SHALL provide Drydock project state and optional
project-scoped agent definitions. Installing an agent-agnostic Git pre-commit
backstop SHALL remain an explicit Owner-approved write under `.git/hooks/` and
SHALL never overwrite an existing hook.

#### Scenario: Plugin installed before repository init
- **WHEN** the plugin is installed in a fresh Codex task
- **THEN** the plugin safety floor may load after trust, while readiness still
  reports the repository lifecycle as uninitialized

#### Scenario: Repository initialized
- **WHEN** initialization completes
- **THEN** the repo receives project state and agent definitions without
  duplicating the plugin hook implementation
