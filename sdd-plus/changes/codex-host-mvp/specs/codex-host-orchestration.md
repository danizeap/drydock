# Spec Delta: codex-host-mvp

Capability: codex-host-orchestration

## ADDED Requirements

### Requirement: Codex pilots through peer adapters
The Codex host SHALL own orchestration and side-effect authority while treating
configured planning/review models as epistemic peers. A peer may raise blocking
concerns; unresolved disagreement SHALL return to the Owner rather than being
silently overridden or presented as agreement. The negotiation controller
SHALL preserve the behavioral contract already exercised by
`scripts/conductor/negotiate.py`: one structured round at a time, a hard round
cap, and no trust in a convergence flag that contradicts reported blockers.

#### Scenario: Peer and pilot converge
- **WHEN** both adapters report convergence with no blocking concerns within
  the round cap
- **THEN** the host produces an agreed plan and audited delegation map

#### Scenario: Disagreement remains at the cap
- **WHEN** blocking concerns remain at the hard round cap
- **THEN** the host stops model calls and presents the disagreement to the
  Owner

#### Scenario: Convergence flag contradicts blockers
- **WHEN** a peer returns `converged: true` with one or more blocking concerns
- **THEN** the controller treats the result as not converged and either runs
  another bounded round or returns the unresolved contradiction at the cap

### Requirement: Claude is an optional, bounded, structured peer
The Claude adapter SHALL distinguish absent, unauthenticated, unavailable,
rate-limited, malformed, and ready states. It SHALL use read-only/no-tool
permissions in the side-effect sense: only the schema-return
`StructuredOutput` tool may be exposed, while repository, shell, web, Chrome,
MCP, and other side-effect tools remain unavailable. It SHALL use no session
persistence, a bounded timeout and usage ceiling, secret/path guards before
spawn, and schema-validated output.

#### Scenario: Installed but unauthenticated
- **WHEN** `claude auth status` reports no login
- **THEN** the adapter reports `peer_unavailable: unauthenticated`, sends no
  repository content, and spends no model quota

#### Scenario: Peer tool surface is bounded
- **WHEN** the Claude peer process starts
- **THEN** its explicit built-in-tool allowlist contains only
  `StructuredOutput`, safe mode disables local customizations, strict MCP
  configuration prevents configured MCP servers from loading, and Chrome is
  disabled

#### Scenario: Misleading success subtype
- **WHEN** the Claude process exits non-zero or returns `is_error: true` while
  another field says `success`
- **THEN** the adapter treats the result as failure and does not accept its
  payload as a critique

#### Scenario: Peer cost is non-finite
- **WHEN** a peer envelope or configured budget contains `NaN`, infinity, or
  another non-finite number
- **THEN** strict JSON/numeric validation rejects it and the cost ceiling is
  not treated as proven

#### Scenario: Claude becomes unavailable mid-workflow
- **WHEN** authentication, quota, timeout, or service failure prevents a peer
  round
- **THEN** Drydock remains the Codex-hosted governor but does not claim
  two-brain convergence

#### Scenario: Cross-model capability is declared proven
- **WHEN** a release or readiness report claims that the Claude peer path works
- **THEN** evidence includes an opt-in authenticated live round trip on the
  supported local CLI, not only fakes or an unauthenticated failure envelope

### Requirement: Peer plan input is bounded untrusted data
Before invoking a peer, the controller SHALL reject an empty plan and any plan
that matches secret-bearing input policy. It SHALL frame accepted plan content
as untrusted data behind a boundary marker that the plan content cannot close.
The peer response SHALL use the existing structured critique fields:
convergence, blocking concerns, gaps, risks, and a per-task owner/model-tier
decomposition.

#### Scenario: Empty plan refused before spawn
- **WHEN** the proposed plan is empty or whitespace-only
- **THEN** the controller returns a structured input error and does not invoke
  Claude or another peer

#### Scenario: Secret-bearing plan refused before spawn
- **WHEN** the plan matches the outbound secret policy
- **THEN** the controller refuses it before authentication, model, or process
  invocation

#### Scenario: Plan contains the current boundary marker
- **WHEN** plan content includes the proposed boundary marker
- **THEN** the controller deterministically escalates the marker until the plan
  cannot close its own data fence

#### Scenario: Structured critique returned
- **WHEN** a valid plan reaches an available peer
- **THEN** its schema-validated critique contains convergence, blockers, gaps,
  risks, and a justified task decomposition with owner and model tier

### Requirement: Execution agents are right-sized and project-scoped
The Codex host SHALL support project-scoped agent definitions and explicit
model/reasoning tiers for bounded advisory and execution roles. Their task
message SHALL be minimal and their results SHALL remain subject to cross-review
and verification. A native nested agent whose permissions can inherit a live
parent override SHALL NOT be used as the containment boundary for a mutating
task.

#### Scenario: Project agent selected
- **WHEN** the plan assigns a bounded non-mutating task to a configured project
  agent
- **THEN** the spawned agent uses the configured role and model and receives
  only the task context selected by the pilot

#### Scenario: Parent context excluded
- **WHEN** the pilot requests a fresh execution context
- **THEN** the spawn uses a no-history/fresh-context mode and the task does not
  inherit unrelated parent conversation content

### Requirement: Fuel governance protects coding pace rather than a spend cap
Routing SHALL treat the Owner-configured minimum useful coding duration as a
pace target, not a maximum budget. Flagship peers SHALL spend their effort on
planning, architectural judgment, and cross-review while bounded execution is
assigned to the smallest model proven suitable. If quota, reset, or burn-rate
evidence is unavailable, the controller SHALL report that the pace forecast is
unavailable rather than claim the target is guaranteed.

#### Scenario: Pace forecast is healthy
- **WHEN** measured remaining capacity and reset timing support the configured
  coding-duration target
- **THEN** the controller does not conserve solely to minimize spend

#### Scenario: Pace target is at risk
- **WHEN** measured burn indicates the configured duration is at risk
- **THEN** the controller recommends a lower-cost executor, a handoff, or task
  reshaping while preserving required proof and flagship judgment

#### Scenario: Task is judgment-heavy but not cleanly delegable
- **WHEN** a task cannot be split into a small coupled unit or a wide mechanical
  sweep without losing important judgment
- **THEN** the pilot escalates or keeps the task with a capable model rather
  than forcing it onto a cheap executor

### Requirement: Mutating execution is isolated from the Owner working tree
Every mutating task SHALL run through a dedicated mutation runner that creates
a Git worktree and fresh task branch from a captured base commit, then launches
a separate ephemeral Codex process with a fixed `workspace-write` sandbox and
that canonical worktree as its working root. The calling pilot SHALL NOT be
able to override the process root or sandbox flags. The runner SHALL NOT fall
back to a native nested writer if process isolation cannot be established.
The reserved worktree container SHALL be inside the repository workspace and
SHALL be Git-ignored before mutation starts.

When the tested Codex build requires user configuration to retain repository
trust, the runner SHALL report that configuration as part of the trusted
computing base rather than claiming a clean-config child. It SHALL ignore
exec-policy rules and pin command-line overrides that disable configured MCP,
web/network access, additional writable roots, login shells, broad inherited
environment, and plugin/app/browser/computer-use feature surfaces. A host that
cannot accept those controls SHALL fail closed.

The runner, not the sandboxed worker, SHALL own every Git metadata mutation,
including worktree and branch creation. Post-worker inspection SHALL validate
the worktree `.git` control link against the Git administrative directory
captured from trusted main-repository metadata at creation time, and every
worktree Git invocation SHALL use explicit `--git-dir` and `--work-tree`
arguments. Diff extraction SHALL use a temporary index and temporary object
store rather than the Owner index or shared object store. The worker SHALL be
limited to working-tree file changes, tests, and read-only Git inspection; it
SHALL NOT depend on write access through the worktree's linked `.git` pointer
into the main repository. Runner ownership SHALL NOT weaken the separate
no-auto-merge and deliberate-integration gates.

After worktree creation and before worker launch, the runner SHALL directly
fingerprint a byte- and entry-bounded Git control surface that includes the
repository/worktree configuration, active HEAD and ref state, indices, hooks,
attributes/excludes, object alternates, replacement state, and trusted
worktree administrative pointers. It SHALL terminate the supported worker
process boundary and compare that fingerprint before the first post-worker Git
command. Any drift or unsafe link/type/link-count in that control surface SHALL
refuse every post-worker Git command. Runner-controlled Git invocations SHALL
also pin executable local-config keys including filesystem monitoring, hook
paths, external attributes, and external diff behavior. The runner SHALL
resolve the Git executable from absolute PATH entries before delegation and
invoke that pinned absolute path thereafter. It SHALL refuse before worktree
creation when repository/worktree-local Git config contains external
clean/smudge/process filters or include directives whose executable/control
bytes are outside the bounded fingerprint. The runner SHALL recheck the Git
control fingerprint after extraction.

The worker process SHALL start inside a runner-owned process-tree boundary
before its code runs. On Windows this boundary SHALL be a kill-on-close Job
Object or a proven equivalent, and the runner SHALL capture the exact process
identity while the process is still suspended inside that boundary. This
mechanism proves descendant lifetime shutdown, not filesystem confinement by
itself. A POSIX process group SHALL be reported as best-effort cleanup rather
than hostile descendant containment, and SHALL NOT clear a gate until a
stronger boundary is proven. The runner SHALL terminate the supported complete
boundary and prove the direct worker identity absent before it releases the
lease, fingerprints state, or extracts a diff.

Before post-worker Git inspection and before cleanup, the runner SHALL scan the
worktree without following links and reject any symbolic link, Windows
junction, other reparse point, or multi-linked regular file. The scan SHALL
have a finite entry bound and SHALL refuse before extraction or cleanup when
that bound is exceeded. Worker changes to `.gitattributes` SHALL invalidate
the review diff; diff extraction SHALL disable external diff and
text-conversion commands.

The runner SHALL hold an atomic exclusive lease keyed by the canonical
worktree path for the worker process lifetime. Concurrent writers SHALL receive
distinct worktrees and leases. A lease record SHALL bind the canonical
worktree, exact worker process identity, start time, and worker deadline. It
SHALL be reclaimable only after a stale threshold strictly greater than the
worker timeout plus cleanup grace, and only after the reclaiming runner proves
that the recorded process identity is no longer alive. If process liveness
cannot be established, reclamation SHALL refuse rather than risk creating a
second writer. The runner SHALL fingerprint the Owner branch and working tree
before execution and again after worker quiescence but before diff extraction.
If the pre-extraction fingerprint differs, it SHALL NOT extract or evaluate
delegated changes. It SHALL recheck Owner state after extraction as defense in
depth. Any drift invalidates the result and blocks integration. The existing
`codex-conductor`
worktree-containment contract is the behavioral baseline, not an implementation
dependency.

#### Scenario: Agent performs a mutating task
- **WHEN** a bounded execution task is delegated with write permission
- **THEN** a separate process can write inside only its dedicated worktree and
  task branch, while an attempted write into the sibling Owner checkout is
  denied by the fixed sandbox

#### Scenario: Parent has wider permissions
- **WHEN** the pilot runs with `danger-full-access` or another write-capable
  parent mode
- **THEN** the mutation process still receives the runner-fixed
  `workspace-write` sandbox and dedicated working root

#### Scenario: Worker produces a reviewable change
- **WHEN** the sandboxed worker changes files and returns its result
- **THEN** the runner validates the linked Git control file and builds the
  review diff with an isolated temporary index/object store; neither the
  worker nor snapshot extraction writes the Owner index or shared object store

#### Scenario: Worker poisons its writable Git control file
- **WHEN** the worker deletes or redirects its worktree `.git` file
- **THEN** the runner rejects the result before any post-worker Git command
  and does not follow the redirected path

#### Scenario: Worker poisons executable Git configuration
- **WHEN** a worker changes repository-local `core.fsmonitor`, `core.hooksPath`,
  an active ref/index, or another fingerprinted Git control path
- **THEN** the direct fingerprint check rejects the result before any
  post-worker Git command, and the configured executable sentinel is not run

#### Scenario: Worker plants a Git executable in its worktree
- **WHEN** a worker creates `git`, `git.exe`, or another executable-search
  candidate in the assigned working root
- **THEN** every runner-owned Git command continues to invoke the absolute Git
  executable pinned before delegation

#### Scenario: Local Git configuration can execute filters or external includes
- **WHEN** repository/worktree-local config defines a clean, smudge, or process
  filter or includes config outside the fingerprinted control surface
- **THEN** mutation refuses before creating the worktree or spawning the worker

#### Scenario: Worker leaves a background descendant
- **WHEN** the direct worker exits while a descendant remains alive
- **THEN** the runner terminates the complete process boundary before
  fingerprinting or diff extraction, so no descendant can mutate after the
  reviewed snapshot

#### Scenario: Worker plants a Windows junction
- **WHEN** the worktree contains a no-privilege directory junction or another
  reparse point before extraction or cleanup
- **THEN** the runner refuses before `git add`, diff extraction, or recursive
  worktree removal and does not traverse the target

#### Scenario: Worker plants a hardlink alias
- **WHEN** a regular worktree path has more than one filesystem link
- **THEN** extraction and cleanup refuse before treating the aliased bytes as
  worktree-owned

#### Scenario: Worker floods the worktree boundary scan
- **WHEN** a worktree contains more entries than the configured finite scan
  bound
- **THEN** the runner refuses before Git extraction or recursive cleanup and
  does not report the uninspected tree as reviewable evidence

#### Scenario: Worker changes Git attributes
- **WHEN** a worker adds or modifies `.gitattributes` to hide changed content
- **THEN** the review diff is invalidated rather than accepted with suppressed
  content

#### Scenario: POSIX descendant boundary is not proven
- **WHEN** the host provides only a process group that a descendant can escape
  with a new session
- **THEN** readiness labels cleanup best-effort and the boundary cannot clear a
  green gate

#### Scenario: Separate process cannot be established
- **WHEN** the runner cannot prove the exact worktree root, sandbox flags,
  exclusive lease, or process start
- **THEN** mutation is BLOCKED and no nested-agent writer is substituted

#### Scenario: Reserved container is not ignored
- **WHEN** `.drydock-worktrees/` is not matched by the repository ignore rules
- **THEN** mutation refuses before creating the task worktree and directs the
  Owner to run Drydock initialization/update

#### Scenario: Tasks run in parallel
- **WHEN** two or more mutating tasks execute concurrently
- **THEN** each writer receives a distinct canonical worktree, branch, separate
  process, and exclusive lease rather than sharing a mutable checkout

#### Scenario: Owner checkout drifts during execution
- **WHEN** the captured Owner branch or working-tree fingerprint changes before
  the worker result is accepted
- **THEN** the result is rejected as contaminated before diff extraction, no
  delegated change evidence is reported, and worker success does not clear it

#### Scenario: Timed-out worker leaves a stale lease
- **WHEN** a lease is older than the worker timeout plus cleanup grace and the
  recorded exact worker process identity is proven absent
- **THEN** a runner may reclaim that lease before reusing or cleaning its
  canonical worktree

#### Scenario: Prior worker liveness is uncertain
- **WHEN** the stale threshold has passed but the runner cannot prove that the
  recorded worker process identity is gone
- **THEN** the lease remains exclusive and a second writer is refused

#### Scenario: Lease timing is non-finite
- **WHEN** a lease record contains `NaN`, infinity, overflow-to-infinity, or an
  invalid cleanup grace
- **THEN** reclamation and cleanup refuse rather than treating the record as
  stale

### Requirement: Delegated results never merge or turn green by accident
The execution adapter SHALL decide gate applicability before pass/fail, SHALL
keep N/A distinct from failure, and SHALL never report green for timed-out,
not-run, malformed, or untrusted test evidence. It SHALL never auto-merge. Its
structured result SHALL include the worktree, branch, diff, changed files,
ignored worker artifacts, test evidence, trust/applicability verdict, and
`merged: false`. A mutation-only result SHALL remain non-green:
verification-applicable work SHALL be `awaiting_verification`, ignored
artifacts SHALL receive a distinct blocking stage, and inert test-N/A work
SHALL remain `review_required`.

#### Scenario: Delegation times out
- **WHEN** an execution agent times out after making partial changes
- **THEN** the partial work may be retained for inspection but the result is
  non-green and cannot clear a gate

#### Scenario: Test evidence is absent or untrusted
- **WHEN** a code/behavior change has no test result or the test command/result
  cannot be trusted
- **THEN** the verdict is blocked or unverifiable, never green

#### Scenario: Worker exits successfully without changing files
- **WHEN** the worker process exits zero but its task worktree has no changed
  files
- **THEN** the runner returns `no_changes` and does not treat absence of a
  mutation as completion evidence

#### Scenario: Worker creates ignored artifacts
- **WHEN** post-worker inspection finds files excluded from the review diff by
  ignore rules
- **THEN** the result lists those paths and remains BLOCKED until they are
  deliberately inspected or discarded

#### Scenario: Changed path type is unknown
- **WHEN** a worker changes an extensionless or unclassified path such as
  `Dockerfile`, `Makefile`, shell/PowerShell, Terraform, JSON, or Gradle input
- **THEN** verification is applicable by default; only a small inert text/doc
  allowlist may be test-not-applicable, and that N/A result is still not green

#### Scenario: Reviewable delegation finishes
- **WHEN** an isolated task returns a diff and gate evidence
- **THEN** it reports `merged: false` and waits for deliberate sequential
  review and integration

### Requirement: Worktree cleanup has a narrow blast radius
Automatic cleanup SHALL target only the exact temporary worktree created for
the task, a task branch with the reserved Codex prefix, and that worktree's
exact lease record. Orphaned lease cleanup SHALL be confined to the reserved
lease directory and SHALL use the same stale-threshold and dead-process proof
required for lease reclamation. Cleanup SHALL refuse to delete any other
worktree, branch, or lease.

#### Scenario: Cleanup receives an unrelated branch
- **WHEN** cleanup is asked to delete a branch outside the reserved task prefix
- **THEN** the branch and worktree are left intact and the refusal is reported

#### Scenario: Cleanup encounters an orphaned lease
- **WHEN** a reserved lease is stale and its recorded worker process identity
  is proven absent
- **THEN** cleanup may remove only that exact lease and its bounded task
  worktree/branch targets

#### Scenario: Unsafe alias blocks automatic cleanup
- **WHEN** cleanup finds a junction, reparse point, symbolic link, hardlink, or
  invalid regular-file link count inside the reserved worktree
- **THEN** it refuses recursive removal, lists the unsafe paths, and requires
  exact non-traversing manual remediation before bounded cleanup is retried

### Requirement: Independent verification uses a separate read-only process
The verifier SHALL run in a separate ephemeral Codex process whose read-only
sandbox, model, timeout, output schema, and working root are fixed by the
verifier runner and cannot be widened by the calling agent. This establishes
process, context, and permission isolation. It SHALL NOT by itself be described
as cross-model or cross-vendor epistemic independence. The working root SHALL
be described as task context, not a read-confinement boundary, unless an
independent probe proves reads outside it are denied on the current host.

#### Scenario: Parent has write-capable permissions
- **WHEN** the pilot runs with workspace-write or danger-full-access
- **THEN** the verifier still runs in a separate process with read-only sandbox
  and a write attempt is denied

#### Scenario: Nested verifier requested
- **WHEN** a custom nested agent would inherit a write-capable live parent
  override
- **THEN** it is not accepted as the independent verifier boundary

#### Scenario: Verifier uses the same model family
- **WHEN** the separate verifier is another Codex-family model or process
- **THEN** the result may satisfy the isolation boundary but readiness does not
  claim an independent epistemic vantage from that fact alone

#### Scenario: Read-only process can inspect outside its working root
- **WHEN** a host permits read-only access beyond the verifier's `-C` root
- **THEN** readiness reports write isolation only and does not claim
  root-confined reads

### Requirement: LaunchGuardian is a candidate-bound workflow gate
Every mutating Codex workflow SHALL include a `security_review` phase after the
exact-candidate full proof and before independent verification, integration, or
push. The phase SHALL run LaunchGuardian in framework mode with strict scanners
against a fresh materialization of the exact clean candidate commit. The caller
SHALL NOT choose the executable, target root, output directory, framework mode,
strictness, or required scanner set.

The runner SHALL bind the candidate commit and v2 executable fingerprint,
observed LaunchGuardian launcher digest and reported version, exact command
contract, bounded report bytes and digest, LGF validation state, launch status,
open blocking findings, and scanner availability into the workflow evidence.
The native scanner process is not host-filesystem write-confined. The runner
SHALL compare the Owner checkout identity before and after execution and fail
closed on detected drift, while disclosing that this is detection rather than
prevention. The selected Python environment, `PATH`, LaunchGuardian package,
scanner executables, and operating system remain trusted. The evidence is
user-writable identity and coordination data, not authenticated attestation or
toolchain provenance proof.

The controller SHALL NOT trust a caller-supplied `passed` outcome by itself.
Before advancing past `security_review`, it SHALL reload the keyed security
record and raw report from the external state store, revalidate their record
key, exact consumed admission (including objective, plan, mechanism, and prior
gates), candidate fingerprint, fixed command contract, report digest,
observed process result, bounded record age, structural acceptance, and
non-zero-exit rule, and refuse missing, malformed, stale, future-dated,
replayed, or non-accepted evidence. The record key SHALL cover every stored
security-result field other than the key itself.

Only `APPROVED` or `APPROVED_WITH_DISPOSITIONS` with valid LGF configuration,
zero open blocking findings, and every expected scanner (`gitleaks`, `semgrep`,
`trivy`, `frontend_exposure`, and `api_surface`) reporting `ran` SHALL pass.
Missing LaunchGuardian, timeout, non-zero exit, malformed or oversized report,
wrong candidate, invalid LGF, skipped or incomplete validation, a missing,
disabled, unavailable, or failed scanner, another launch status, or any open
blocking finding SHALL remain non-green.

A substantive security finding SHALL return the workflow to mutation and
invalidate candidate-dependent evidence. A procedural scanner failure MAY
retry only `security_review` and only while the exact candidate, plan,
mechanism, and prior-gate digests remain unchanged. No security result may
authorize side effects or widen Owner authority.

#### Scenario: Exact candidate passes the strict security gate
- **WHEN** the full proof passed and LaunchGuardian returns valid candidate-bound
  evidence with an accepted launch status, valid LGF configuration, zero open
  blockers, and all five expected scanners reporting `ran`
- **THEN** the controller records the `security_review` evidence and may admit
  independent verification for that same candidate

#### Scenario: Scanner is absent, disabled, unavailable, or failed
- **WHEN** the executable cannot start or any expected scanner does not report
  `ran`
- **THEN** the security phase is non-green and verification, integration, and
  push remain unavailable

#### Scenario: Security report belongs to another candidate
- **WHEN** the report or workflow admission is bound to a different commit or
  executable fingerprint
- **THEN** the runner refuses it before the report can satisfy the security gate

#### Scenario: Caller claims PASS without accepted security evidence
- **WHEN** a consumed `security_review` admission is finished as `passed` with
  an arbitrary, missing, stale, or tampered evidence key
- **THEN** the controller refuses the transition and independent verification,
  integration, and push remain unavailable

#### Scenario: LaunchGuardian finds a substantive blocker
- **WHEN** LGF validation is invalid, launch status is blocking, or an open
  blocking finding remains
- **THEN** the candidate returns to mutation and all candidate-dependent
  downstream evidence is invalidated

#### Scenario: Scanner transport fails without changing the candidate
- **WHEN** a timeout, unavailable executable, malformed report, or scanner
  execution failure occurs and the exact candidate and prior gates remain
  unchanged
- **THEN** a fresh Owner-authorized resume may retry only `security_review`
  without repeating accepted plan, mutation, cross-review, or proof gates

### Requirement: Verifier verdicts bind to repository state
The verifier runner SHALL record HEAD and a working-tree fingerprint before
verification, embed the exact expected values into the output schema, require
the verifier to echo them in a state-binding object, deeply validate every
nested verdict field, terminate and prove its process-tree boundary quiescent,
and only then re-check the fingerprint and read the verdict. The echoed state
binding is freshness/anti-replay evidence; it does not prove the model observed
the state. A malformed, misbound, changed, or unidentifiable tree/verdict SHALL
invalidate the verdict.

#### Scenario: Tree remains frozen
- **WHEN** HEAD and the working-tree fingerprint match before and after
  verification
- **THEN** the verdict identifies that exact repository state

#### Scenario: Tree changes during verification
- **WHEN** any bound fingerprint component changes before the verifier finishes
- **THEN** the result is BLOCKED or stale and cannot clear verification

#### Scenario: Verifier emits a shallow-schema lookalike
- **WHEN** a parseable verdict has a wrong nested type, an extra field, or a
  state binding that does not exactly match the expected HEAD/fingerprint
- **THEN** the runner reports an invalid verdict and never accepts `PASS`

#### Scenario: Verifier leaves a background descendant
- **WHEN** the direct verifier exits but a child process remains
- **THEN** the runner terminates the complete supported boundary before the
  post-run fingerprint or verdict-file read
