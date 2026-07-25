# Spec Delta: privileged-test-runner-hardening

Capability: codex-conductor

## MODIFIED Requirements

### Requirement: Never green on a result the gate cannot trust
Before Codex discovery, worktree creation, or delegation, the mutation runner
SHALL compile an optional test plan into one or more structured argument
vectors. Structured argv SHALL be authoritative. The legacy `--test-cmd`
adapter SHALL accept only simple commands and `&&` short-circuit chains; it
SHALL reject pipes, sequencing/background operators, `||`, redirects,
newlines, command substitution, malformed quoting, or any unrecognized shell
syntax without executing it. An invalid plan SHALL return a structured
`test_plan` failure before Codex or a test process starts.

Each step SHALL name a bare executable rather than a caller-selected path. The
runner SHALL resolve that executable to an absolute file from an absolute
parent PATH entry before delegation, and SHALL refuse an executable beneath a
temporary root writable by the mutating worker. Before the mutating worker
starts, the runner SHALL also discover, validate, and pin a model-free Codex
sandbox runner. Post-worker execution SHALL invoke the captured absolute test
executable through that pinned sandbox with `shell=False`; no direct-controller
fallback is allowed. Shell launchers and Windows batch/command shims SHALL be
refused when selected directly. Drydock SHALL NOT claim that pinning the
top-level executable prevents an allowed executable from invoking a shell or
another runner transitively. Known indirection and interpreter launchers SHALL
produce an advisory stating that their internal execution is unproven. The
complete plan SHALL have finite step, argument, and character bounds. Steps SHALL
execute sequentially under one total timeout budget and stop at the first
non-zero result, preserving the safe failure-propagation behavior formerly
provided by `&&`.

The sandbox invocation SHALL request writes only to the assigned worktree and
SHALL request direct network denial. Native Windows execution SHALL pin the
elevated sandbox backend rather than inherit a weaker Owner default, and
managed constraints SHALL remain included. Its result SHALL identify those as
requested configuration rather than per-run verified facts and SHALL disclose
any platform boundary that was not established. In particular, native-Windows
filesystem read isolation SHALL NOT be claimed from the current mechanism: the
local point-in-time platform spike observed out-of-worktree write denial and
direct-network denial, but an explicit deny profile still read the Owner
checkout. This is requested write/network containment with point-in-time probe
evidence, not full host isolation or per-run boundary verification.

When a sandbox readiness probe or launched test exceeds its deadline, the
runner SHALL attempt bounded process-tree termination using a POSIX process
group or Windows tree termination. The refusal or timeout result SHALL state
whether cleanup was confirmed; test timeout evidence SHALL also state the
mechanism and that descendants escaping the grouping mechanism may survive.
Tests execute after the review diff is extracted; the result SHALL disclose
that test-created files may therefore remain unstaged in the retained worktree
even though they are absent from that reviewed diff. Runner delegation SHALL
remain an advisory, and an absent or unverifiable trust signal SHALL remain
non-green.

#### Scenario: Structured argv passes honestly
- **WHEN** the Owner supplies a bounded structured argv test step whose
  executable resolves before delegation and the step exits zero
- **THEN** the runner invokes the captured absolute executable without a shell
  through the pinned Codex sandbox, and the test result may be trusted by the
  existing applicability gate

#### Scenario: Safe legacy command remains usable
- **WHEN** `--test-cmd` contains a simple command or a well-quoted `&&` chain
- **THEN** it is compiled to one or more argv steps and executed sequentially
  without a shell, stopping at the first failure

#### Scenario: Shell syntax is refused before delegation
- **WHEN** a legacy test command contains a pipe, redirect, `;`, bare `&`,
  `||`, newline, command substitution, or malformed quoting
- **THEN** mutation returns `stage: test_plan` before Codex discovery,
  worktree creation, or any test process spawn

#### Scenario: Worker plants a test executable
- **WHEN** the worker creates an executable in its assigned worktree with the
  same name as the selected test runner
- **THEN** post-worker test execution still invokes the absolute executable
  resolved before delegation

#### Scenario: PATH resolves inside worker-writable temporary storage
- **WHEN** the first matching executable is beneath `TEMP`, `TMP`, `TMPDIR`, or
  the platform temporary root that the mutating worker can write
- **THEN** test-plan compilation refuses it rather than pinning a path whose
  bytes the worker can replace

#### Scenario: Direct known shell escape is refused
- **WHEN** a structured or legacy test step selects `bash`, `sh`, `cmd`,
  PowerShell, or a Windows `.cmd`/`.bat` shim
- **THEN** compilation refuses rather than relabelling shell execution as
  structured no-shell execution

#### Scenario: Allowed executable invokes a shell transitively
- **WHEN** a structured or legacy test step selects a known indirection or
  interpreter launcher such as `env`, `xargs`, Python, or Node
- **THEN** Drydock pins and invokes that top-level executable without an
  implicit shell, reports that its internal execution is unproven, and relies
  on the requested sandbox restrictions rather than claiming transitive shell
  prevention

#### Scenario: Multi-step timeout is globally bounded
- **WHEN** a structured plan has several steps
- **THEN** they share one total deadline rather than receiving the full timeout
  independently

#### Scenario: Timed-out test leaves descendants
- **WHEN** a sandboxed test exceeds the shared deadline after spawning a child
  process
- **THEN** the runner attempts bounded process-tree termination and the result
  reports the cleanup mechanism, confirmation state, and escaped-descendant
  limitation rather than silently assuming the child is gone

#### Scenario: Sandbox readiness fails closed
- **WHEN** a test plan is present but the installed Codex CLI cannot prepare its
  model-free sandbox command
- **THEN** mutation returns a structured `test_sandbox` failure before worktree
  creation or mutating delegation, no test runs as the controller, and a
  timed-out readiness process receives the same bounded tree-cleanup attempt

#### Scenario: Sandboxed test restrictions are reported honestly
- **WHEN** project-authored test code runs through the configured sandbox
- **THEN** the result reports the requested worktree write scope and
  direct-network denial separately from per-run verified behavior

#### Scenario: Worker config requests a weaker sandbox
- **WHEN** the worktree's project config requests legacy
  `danger-full-access` sandboxing or a danger-full-access default permission
  profile
- **THEN** the explicit CLI test profile remains authoritative, managed
  constraints remain included, and an out-of-worktree write is denied

#### Scenario: Native Windows read boundary is reported honestly
- **WHEN** a sandboxed test result is produced on native Windows
- **THEN** the result reports that worktree-write and direct-network
  restrictions were requested, per-run boundary verification was not
  performed, and host filesystem read isolation remains unestablished

#### Scenario: Tests create files after diff extraction
- **WHEN** project tests create or modify files in a retained worker worktree
- **THEN** the result warns that those unstaged artifacts were not part of the
  previously extracted review diff and must be inspected before any manual
  commit
