# Capability: codex-host-orchestration

Capability: codex-host-orchestration

## Purpose

The Codex-hosted orchestration capability: bounded peer planning, isolated mutation, truthful evidence gates, candidate-bound security review, and separate read-only verification.

## Requirements

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

Only this explicitly enumerated allowlist of benign availability failures MAY
enter the single-pilot workflow: authentication unavailable before spawn, an
exact supported rate-limit marker, a controller timeout with bounded cleanup,
or an ordinary non-zero process exit that carries no structured provider
subtype and is proven to have consumed zero provider cost. A budget ceiling,
policy/refusal/context-limit abort, malformed output, model mismatch, missing
model/cost proof, unknown structured subtype, unmapped stage, or other
contract/control violation SHALL return to the Owner and SHALL NOT authorize
automatic continuation. The default for every unrecognized value is
`return_to_owner`.

For this requirement, "provider cost is proven zero" means a successfully
parsed top-level CLI envelope for the requested model contains a finite numeric
`total_cost_usd` equal to exactly zero. A missing, malformed, negative, or
unavailable cost field is unknown and never proves zero.

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
- **WHEN** one of the four allowlisted benign availability failures prevents a
  peer round
- **THEN** Drydock may remain the Codex-hosted governor in machine-readable
  single-pilot mode while reporting `peer_convergence: not_established`

#### Scenario: Claude times out or its process fails
- **WHEN** a bounded peer call times out with bounded cleanup, or its process
  exits nonzero with no structured provider subtype and provider cost proven
  exactly zero
- **THEN** Codex may continue the governed packet in single-pilot mode without
  claiming peer agreement, cross-model review, or operational readiness

#### Scenario: Failure is not one of the four allowed values
- **WHEN** a structured subtype, stage, or failure class is not explicitly in
  the benign-availability allowlist
- **THEN** the workflow returns to the Owner and SHALL NOT enter automatic
  single-pilot continuation

#### Scenario: Provider budget ceiling aborts the call
- **WHEN** the peer exits with `error_max_budget_usd`
- **THEN** the result is a budget control violation with
  `workflow.action: return_to_owner`, not `continue_codex_only`

#### Scenario: Provider adds an unknown subtype
- **WHEN** a peer failure carries a structured subtype that appears nowhere in
  the controller's allowlist
- **THEN** the result is `unmapped_control_failure` with
  `workflow.action: return_to_owner`

#### Scenario: Ordinary process exits without a provider subtype
- **WHEN** the bounded peer exits nonzero, cleanup is complete, and no
  structured provider subtype or contract output exists, and provider cost is
  proven zero
- **THEN** the explicit ordinary-process-exit allowlist entry may enter
  single-pilot with convergence not established

#### Scenario: Bare non-zero exit has unknown or positive provider cost
- **WHEN** the bounded peer exits nonzero without a structured subtype but its
  provider cost is unknown or greater than zero
- **THEN** the failure is not proven benign and returns to the Owner

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

#### Scenario: Optional worktree config is enabled but absent
- **WHEN** `extensions.worktreeConfig` is true and the exact current-worktree
  `config.worktree` file does not exist
- **THEN** the runner treats that optional scope as empty rather than a Git
  command failure, while an existing file is accepted only as a regular,
  single-link, non-reparse file whose exact keys still pass the include and
  external-filter checks

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

An official workflow proof admission SHALL accept only
`scope=full_required_suite`; an intermediate proof SHALL be refused before test
process spawn. Before advancing from `proof` to `security_review`, the
controller SHALL reload the keyed proof record from external state and require
an exact-fingerprint, zero-exit, non-timeout, structurally accepted
`full_required_suite` result. A caller-supplied passed outcome or intermediate
record key SHALL NOT satisfy that transition.

After the Git archive path set, regular-file bytes, and executable-mode
semantics have been proven equal to the committed Git tree, the proof root
SHALL be materialized only from those already-verified Git blob bytes. It SHALL
NOT delegate path creation to `tarfile.extract()` or
`tarfile.extractall()`. The in-memory archive SHALL NOT occupy a path inside
the proof root, so a committed file named `.archive.tar` remains ordinary
candidate content rather than colliding with runner state.

#### Scenario: Archive equality is proven before materialization
- **WHEN** the archive and committed tree have identical safe regular-file
  paths, blob bytes, and executable modes
- **THEN** the runner writes only the verified Git blob bytes beneath the
  fresh root and never invokes a tar extraction primitive

#### Scenario: Candidate tracks the runner's former archive filename
- **WHEN** the exact candidate contains a regular file named `.archive.tar`
- **THEN** that committed blob is materialized and retained like every other
  candidate file; no runner-owned archive path overwrites or deletes it

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
security-result field other than the key itself. The controller SHALL reload
keyed evidence for `passed`, `technical_blocker`, and `procedural_failure` and
SHALL reject a caller-supplied classification that differs from the stored
result. A procedural transport failure may preserve the candidate only when a
fresh keyed record binds the exact consumed admission, candidate, failure
stage, process/liveness result, and unchanged Owner checkout.
The stored failure stage SHALL be cross-consistent with measured process facts:
an unavailable executable has no started process, a timeout has a discovered
executable plus `timed_out=true` and absent process identity, and invalid output
does not masquerade as a timeout. A blocking report remains a technical
blocker even when the scanner process also exits non-zero.

Only `APPROVED` or `APPROVED_WITH_DISPOSITIONS` with valid LGF configuration,
zero open blocking findings, and every expected scanner (`gitleaks`, `semgrep`,
`trivy`, `frontend_exposure`, and `api_surface`) reporting `ran` SHALL pass.
The runner SHALL recompute severity, scanner, status, gate, blocking, and
per-scanner counts from the actual finding rows and reject reassigned,
invented, or otherwise contradictory aggregates. Finding sources SHALL be
limited to the five expected scanners plus LaunchGuardian's `config`,
`config_discovery`, and `launch_policy` producers; finding status SHALL be one
of `open`, `fixed`, `accepted`, `false_positive`, `not_applicable`, or
`needs_review`. The parser SHALL additionally enforce the pinned 0.2.0
producer's narrower cross-field semantics: ordinary findings are `open`,
`needs_review` is limited to the named unused-disposition policy finding, and
`not_applicable` requires a non-Critical Semgrep finding whose exact rule and
review metadata match a valid, unique configured disposition. Unsupported
status reclassification, a disposition/status mismatch, a Critical
disposition, or placeholder/future-dated review evidence SHALL be malformed.
The parser SHALL recompute launch status and LGF validation status from the
validated findings, scanner states, dispositions, and LGF result.

The per-scanner check SHALL cover every availability state using the pinned
report producer's semantics: `ran` counts scanner finding rows,
`unavailable` binds the external scanner's exact strict-mode
`scanner_unavailable` row while its detected count remains zero, failed
execution binds no scanner rows and zero counts, and `disabled` binds the
scanner's named `config/scanner_disabled` row. Unknown scanner states SHALL be
malformed. Process timeout cleanup and the final stdout/stderr drain SHALL
remain bounded even when descendant pipe handles remain open.
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

### Requirement: Orchestration stdin is bounded exact UTF-8
Codex orchestration entry points that accept a workflow payload, Owner action,
peer review plan, mutation task, verification prompt, or integration request
on stdin SHALL read the raw stdin byte stream once, enforce the input's
existing byte ceiling before decoding, and decode strictly as UTF-8 independent
of the host locale. The workflow payload, Owner action, and integration request
ceilings SHALL be 64 KiB; the peer review plan ceiling SHALL be 512 KiB; and
the mutation task and verification prompt ceilings SHALL be 256 KiB.
Malformed UTF-8, an unavailable byte stream, an unreadable stream, or an input
over its ceiling SHALL fail closed before provider execution or repository
mutation.

#### Scenario: Windows locale differs from UTF-8
- **WHEN** raw UTF-8 stdin contains a non-ASCII code point while the host text
  wrapper uses a legacy Windows encoding
- **THEN** every orchestration entry point dispatches the exact Unicode text
  decoded from the original UTF-8 bytes

#### Scenario: Stdin is malformed or oversized
- **WHEN** stdin is not valid UTF-8 or exceeds the entry point's byte ceiling
- **THEN** the entry point returns a structured non-green input result without
  invoking a provider or mutating the repository

### Requirement: One objective has one current plan and explicit lineage
The controller SHALL maintain exactly one current structured technical-plan
revision for an Owner objective. Objective identity SHALL include an immutable,
Owner-issued opaque identifier that is independent of editable objective or
plan prose. Every revision SHALL carry that identifier, the objective contract
digest, a positive monotonically increasing revision, its own canonical digest,
and the exact digest it supersedes except for revision one. A replacement whose
objective identifier or predecessor is missing, stale, or not the current
identity SHALL fail closed.
Superseded revisions MAY remain as bounded audit history but SHALL NOT satisfy a
current peer, mutation, proof, verification, integration, or push gate.

The packet's `plan.md` SHALL be the sole human-readable active plan. Recovery,
negotiation, and verification artifacts may record history or evidence but
SHALL NOT silently become competing active plans.

#### Scenario: A stale recovery plan is presented
- **WHEN** a proposed revision does not name the exact current plan digest
- **THEN** the controller rejects it before provider or worker spawn and keeps
  the existing current revision unchanged

#### Scenario: A valid compact revision replaces the current plan
- **WHEN** the new revision increments by one, names the current digest, and
  preserves the immutable objective identifier within the same validated Owner
  authority
- **THEN** the controller atomically marks the predecessor superseded and the
  new revision current

#### Scenario: Editable prose is renamed
- **WHEN** plan or objective prose changes without a new Owner-issued objective
  identifier
- **THEN** the controller treats it as a revision of the same objective and
  retains its cumulative circuit and history

### Requirement: Owner authority is a deterministic preflight contract
Before any peer, worker, proof, verifier, integration, or push process starts,
the controller SHALL validate a strict structured authority manifest. The
manifest SHALL bind the objective digest, immutable Owner-issued objective
identifier, Owner-action digest, canonical repository root, host task identity,
exact allowed repository paths, allowed actions, optional exact push remote and
branch, resource ceilings, and expiry. Unknown fields, wildcard paths,
non-canonical roots, expired authority, and missing action-specific fields
SHALL fail closed.

The controller SHALL persist a one-time-use ledger for Owner-action digests
outside the repository. Objective creation, supersession, blocked-state resume,
and circuit resolution SHALL atomically consume the exact action digest with
the transition it authorizes. A consumed digest SHALL NOT authorize another
transition. Circuit resolution SHALL additionally bind the action to the exact
opening-snapshot digest.

The current technical plan SHALL declare its required paths, actions, phases,
resource request, exact canonical packet `plan.md` path, and SHA-256 of that
file's current bytes. Every declared value SHALL be a subset of the manifest.
Preflight and every executor admission SHALL re-read that exact repository file
and refuse when its bytes no longer match. Circuit thresholds SHALL be explicit
manifest fields; the configurable defaults are two procedural failures, 900
observed pre-worker seconds, and USD 1.50 observed pre-worker peer spend.
Claude or another peer may audit technical safety but SHALL NOT grant, widen,
interpret, or reconcile Owner authority. A manifest digest identifies the
controller input; it is not cryptographic proof of Owner authorship.

#### Scenario: Plan requests an unapproved checkpoint push
- **WHEN** the plan names a remote, branch, or push action absent from the
  authority manifest
- **THEN** local preflight rejects the plan before a peer call and reports the
  exact unmatched field

#### Scenario: Authority and plan agree
- **WHEN** objective, repository, paths, actions, resources, and optional push
  destination all match or narrow the manifest
- **THEN** preflight records their canonical digests and no peer call is spent
  interpreting authority

#### Scenario: Canonical packet plan changes after peer admission
- **WHEN** the packet's sole active `plan.md` bytes differ from the exact digest
  in the current structured plan
- **THEN** the next executor admission refuses before spawn and the stale
  structured plan remains current only as blocked evidence until explicitly
  revised

#### Scenario: Owner action is replayed
- **WHEN** an Owner-action digest already consumed by any objective transition
  is presented again
- **THEN** preflight refuses the transition without provider or worker spawn

### Requirement: One workflow state machine owns executor admission
The controller SHALL expose one workflow surface that owns the ordered phases
`preflight`, `plan_peer`, `mutation`, `cross_review`, `proof`, `verification`,
`integration`, optional `push`, and terminal `complete` or `blocked`.
Success transitions SHALL be atomic and SHALL accept only the immediately
permitted successor. Failure transitions SHALL be explicit:

- plan-peer blocker plus a valid plan revision returns to `plan_peer`;
- mutation failure may resume `mutation` only when the admission's
  pre-mutation candidate is null, the failed executor returns a null candidate
  digest, and plan identity remains exact; any observed candidate or partial
  candidate identity requires discard/invalidation before another admission;
- cross-review, proof, or verification rejection returns to `mutation` and
  invalidates candidate-dependent downstream evidence;
- integration failure may resume `integration` only when the exact candidate
  and every prior gate remain current;
- push failure may resume `push` only when the exact candidate, clean-tree
  identity, destination, and remote baseline remain current and the failure is
  proven not to have updated the remote.

Every blocked transition SHALL record one permitted resume phase and its exact
preconditions. Resume SHALL require a fresh, one-time Owner action. A plan,
authority scope, or mechanism change invalidates every phase after `preflight`;
a candidate change invalidates cross-review, proof, verification, integration,
and push evidence. The controller SHALL record the exact plan, manifest,
mechanism, candidate, and required prior-gate digests relevant to each
transition.

Existing peer, mutation, proof, verifier, integration, and push implementations
remain separate executors. Every official executor wrapper SHALL atomically
validate and consume one short-lived admission record before its first
expensive call or side effect. The record SHALL bind immutable objective ID,
workflow/run, phase, authority, plan, mechanism, input, required prior gates,
candidate when one exists, a random nonce, and expiry. A consumed, expired,
stale, mismatched, or missing record SHALL refuse before spawn or side effect.

These records are controller-enforced coordination under the disclosed
same-user, user-writable local trusted computing base; they are not signatures
and do not establish hostile-user integrity. A raw manually invoked primitive
may remain available to the Owner or same-user process but, absent direct
tampering with controller state, SHALL NOT advance or satisfy workflow state.
No push executor is available until a dedicated wrapper also proves exact
clean candidate, destination, remote baseline, pushed commit, and post-push
remote identity.

Admission consumption SHALL precede spawn or side effect. A crash after
consumption burns that admission. After its expiry, the controller MAY record
the executor attempt as unknown-cost and issue a fresh admission without a new
Owner action; it SHALL NOT replay the burned nonce. By contrast, a crash after
an Owner-action digest is consumed but before its transition commits burns the
Owner action and requires a fresh Owner action.

The locked, atomically replaced workflow record SHALL be the transition commit
point. Immutable plan bodies SHALL be written before a record points to them.
Every workflow read SHALL verify that the referenced body exists and matches
its recorded digest. A missing or mismatched body SHALL fail closed; an
unreferenced body is an inert orphan and SHALL NOT become current by timestamp
or directory scan.

The official mutation wrapper SHALL consume its mutation admission before
worktree creation. After the worker process tree is quiescent, Owner state and
the Git control surface remain exact, and a second extraction equals the first
review snapshot, the runner MAY create one commit on the isolated Drydock
branch. The runner SHALL use pinned Git execution, disabled hooks and signing,
fixed non-secret candidate identity, and the exact reviewed path set. It SHALL
then require a clean candidate worktree and compute the current v2 executable
fingerprint from that exact commit. The worker itself SHALL NOT stage or
commit. The isolated candidate commit is durable review material; it does not
move the Owner branch or satisfy cross-review, proof, or verification.

The official integration wrapper SHALL accept only a bounded strict-JSON
request binding the exact Owner branch and base commit, Drydock candidate
branch/worktree/commit, packet root, and executable fingerprint. Before
consuming its integration admission it SHALL prove both worktrees clean, the
Owner branch still attached at the base, the candidate branch/worktree at the
admitted descendant commit, and the candidate v2 identity exact. It SHALL
repeat those checks after consumption, perform only a non-hooked
fast-forward-only update, and require the Owner checkout to be clean at the
exact candidate fingerprint afterward. It SHALL NOT push. An integration
failure is resumable only when the wrapper positively proves the complete
Owner fingerprint remained unchanged; an updated or unconfirmable Owner state
is terminal rather than automatically retried or rolled back.

#### Scenario: Pilot attempts mutation after an unproven peer gate
- **WHEN** the current phase is `plan_peer` and convergence is absent, stale, or
  bound to another plan digest
- **THEN** the workflow refuses the mutation transition before worker spawn

#### Scenario: Verified workflow omits push
- **WHEN** the manifest does not authorize push and integration succeeds
- **THEN** the workflow may complete locally without inventing or requesting a
  push phase

#### Scenario: Candidate changes after cross-review
- **WHEN** any candidate byte changes after cross-review
- **THEN** the controller invalidates cross-review and every later gate and
  permits no proof, verification, integration, or push admission

#### Scenario: Official executor receives a replayed admission
- **WHEN** an executor presents an admission nonce already consumed by another
  start attempt
- **THEN** it refuses before provider, worker, command, commit, or push spawn

#### Scenario: Candidate is ready for cross-review
- **WHEN** official mutation produced a non-empty bounded diff without Owner,
  Git-control, ignored-path, timeout, or worker-exit failure
- **THEN** the runner commits exactly that snapshot only on the isolated
  Drydock branch and returns its clean commit and v2 executable fingerprint
- **AND** the Owner branch remains at its original commit with `merged: false`

#### Scenario: Owner checkout drifts before integration
- **WHEN** the Owner HEAD, branch, status, or working-tree fingerprint differs
  from the admitted integration base
- **THEN** integration refuses before consuming the admission or moving a ref

#### Scenario: Integration outcome is ambiguous
- **WHEN** a fast-forward attempt fails and the complete pre-integration Owner
  fingerprint is not positively proven unchanged
- **THEN** the workflow becomes terminally blocked and performs no automatic
  retry, rollback, push, or destructive cleanup

### Requirement: Procedural circuit state survives individual runs
The controller SHALL maintain objective-level circuit evidence outside the
repository across every run ID, retry, and phase entry for the same immutable
objective ID. It SHALL cumulatively count procedural/control failures, phase
entries and reentries, outbound bytes, directly observed elapsed time, and
observed provider spend across the complete workflow. Worker start SHALL NOT
reset, pause, or exclude any counter. Technical peer blockers SHALL NOT be
mislabeled procedural, but their calls, bytes, elapsed time, phase entries, and
observed spend still consume the objective circuit.

Manifest circuit thresholds SHALL be explicit and may narrow but SHALL NOT
exceed controller safety maxima. Opening or closing an individual run SHALL NOT
reset any objective counter. An open circuit SHALL refuse another official
executor. Closing it SHALL require a fresh one-time Owner-action digest bound to
the exact opening-snapshot digest and at least one changed current-plan,
authority-scope, or controller-mechanism digest. The controller SHALL preserve
a monotonically increasing circuit-resolution count. At most one resolution is
permitted for an objective; a later opening is terminal and only an explicitly
Owner-created successor objective with a new immutable ID and predecessor
lineage can proceed.

If provider cost or another capacity signal is unavailable, the controller
SHALL record that axis as unknown rather than zero or enforced. Observable
time, calls, bytes, phase entries, and known spend remain enforced.

#### Scenario: Owner says continue without a material correction
- **WHEN** the objective circuit is open and a fresh run carries unchanged
  plan, authority, and mechanism digests
- **THEN** the controller refuses the run without provider spend even if a new
  Owner-action digest exists

#### Scenario: Controller defect is fixed
- **WHEN** the circuit is open, the mechanism digest changes, and the Owner
  explicitly authorizes resumption
- **THEN** the controller records the resolution lineage, consumes the exact
  action once, preserves cumulative counters and prior runs, increments the
  resolution count, and resumes only the recorded phase

#### Scenario: Cross-review repeatedly rejects changed candidates
- **WHEN** mutation and cross-review reenter after worker start
- **THEN** every entry, elapsed second, outbound byte, and observed provider
  cost continues accumulating against the same objective circuit

#### Scenario: Circuit opens after its one permitted resolution
- **WHEN** an objective whose resolution count is one reaches another circuit
  limit
- **THEN** it becomes terminally blocked and cannot be reset by a new run,
  renamed plan, or replayed Owner action

### Requirement: Later peer rounds review bounded technical deltas
The first plan-peer round SHALL receive the compact current technical plan and
a machine-generated summary of satisfied control preconditions. A later round
SHALL receive stable identifiers and text for unresolved technical blockers,
the exact changed plan fields, and only the bounded context needed to evaluate
those changes. It SHALL NOT replay complete negotiation history, Owner
transcripts, or unchanged standard control prose.

The peer verdict schema SHALL include `insufficient_context`. That verdict is
non-converging and SHALL name the exact additional bounded files, digests, or
questions needed. Input truncation SHALL force `insufficient_context` or local
preflight refusal and SHALL NOT produce convergence. Within the configured
round cap, an insufficient-context verdict is a technical outcome, not a
procedural failure.

The request SHALL define canonical review input as the exact UTF-8 bytes inside
its generated boundary, excluding the boundary and surrounding prompt. It
SHALL declare byte count and SHA-256, and the peer verdict SHALL echo that
digest. A missing or mismatched echo SHALL make convergence unavailable.

Every peer invocation SHALL carry an allowlisted review kind and provider
effort. The official `plan_peer` phase SHALL accept only a plan review and the
official `cross_review` phase SHALL accept only an implementation review.
Review kind and effort SHALL enter durable invocation identity and result
evidence so a cached or active call with different controls is not equivalent.
An unsupported value or phase/kind mismatch SHALL fail before provider spawn.

The structured verdict schema SHALL bound the overall assessment, every
blocker/gap/risk/context item, task text and rationale, and every array.
Implementation review SHALL request an empty task decomposition when no
blocker exists and only minimal remediation tasks when blockers exist. These
bounds limit accepted structured output; they SHALL NOT be described as a
measurement or hard ceiling on provider-side reasoning, hidden tokens, or
total account usage. Requested effort is a provider control and SHALL be
reported as requested configuration rather than observed reasoning volume.

Authority mismatch, invalid phase order, stale plan identity, and local
resource-envelope impossibility are controller preflight failures and SHALL
consume no peer call. A peer may reopen a previously closed technical blocker
only by naming the changed field or dependency that invalidated its closure.

#### Scenario: Round two changes only verifier binding
- **WHEN** the first verdict has one verifier-binding blocker and the plan
  changes only the relevant verifier fields
- **THEN** round two contains that blocker, those changed fields, and bounded
  verifier context rather than the complete round-one request

#### Scenario: The bounded delta omits a required dependency
- **WHEN** the peer cannot evaluate a changed field without a named omitted
  contract or implementation path
- **THEN** it returns `insufficient_context` with that exact bounded request,
  convergence remains false, and the controller does not count the result as a
  procedural transport failure

#### Scenario: Implementation review selects a lower bounded effort
- **WHEN** the controller admits an implementation cross-review with allowlisted
  `medium` effort
- **THEN** the CLI receives that exact effort, the invocation fingerprint and
  evidence bind it, and all digest, context, blocker, and convergence gates
  remain unchanged

#### Scenario: Review output attempts to exceed its schema
- **WHEN** the peer returns more items or text than the structured verdict
  contract allows
- **THEN** the result is malformed and non-converging rather than truncated or
  accepted as partial evidence

### Requirement: Codex coordination does not depend on Owner relay
The normal Codex-hosted workflow SHALL use one Owner-facing task. When a
separate Codex task is deliberately used, the pilot SHALL use available direct
task read/send/wait mechanisms and SHALL preserve task identity in workflow
state. Asking the Owner to copy model output between Codex tasks is a degraded
fallback, SHALL be disclosed as such, and SHALL NOT be the default operating
path.

### Requirement: Workflow payload transport is bounded and non-inheriting
When the host shell cannot deliver the authority/plan payload through stdin,
the controller SHALL write the payload once under its out-of-tree state root
and pass only an absolute path plus expected SHA-256 to the child. The child
SHALL require that path to be a regular non-link file under the canonical state
root, enforce a byte limit, read once into memory, verify and parse that same
buffer, recheck file identity, and delete the file. It SHALL NOT place the
payload body in argv or an inherited environment variable.

On Windows, link/reparse rejection SHALL use metadata from the opened file
handle plus pre/post file identity rather than trusting a path-only precheck.
An executor crash may leave an orphan; payloads older than the bounded
retention window SHALL be reaped only when they are regular non-reparse files
inside the owned payload directory. A failed consume or reaper deletion SHALL
be reported rather than ignored.

#### Scenario: Windows shell delivers empty stdin
- **WHEN** the controller selects file transport for a bounded workflow payload
- **THEN** the child receives only path and digest metadata, consumes the exact
  file once, and no provider or worker inherits the payload body

#### Scenario: Payload file is replaced
- **WHEN** file identity, location, type, size, or SHA-256 differs before or
  during the bounded read
- **THEN** the workflow refuses before state transition or provider spawn

### Requirement: Control-plane rollback fails closed
The workflow-control feature flag SHALL accept only explicit enabled or
disabled values and SHALL be recorded in workflow evidence. Disabled or
malformed state SHALL create no governed workflow and SHALL NOT substitute a
legacy, raw, or unordered executor path.

#### Scenario: Workflow control is disabled
- **WHEN** the feature flag is explicitly disabled
- **THEN** workflow creation refuses before consuming Owner authority or
  starting any provider, worker, proof, verifier, integration, or push action

### Requirement: Every expensive phase and the whole run have explicit resource envelopes
The controller SHALL bind each plan-peer, mutation, cross-review, proof,
verification, integration, and optional push phase to a configured envelope
containing applicable elapsed-time, call, outbound-input-byte, and
provider-budget ceilings. The controller SHALL also enforce cumulative ceilings
over the immutable objective so phase limits, retries, and new run IDs cannot
multiply beyond the Owner's boundary. It SHALL record actual observed values
and SHALL represent unavailable token, cost, or account usage as unknown.
Exhaustion SHALL produce a structured stop or advisory-reroute decision and
SHALL NOT create a PASS or convergence.

Every phase envelope SHALL be subordinate to and SHALL NOT raise the cumulative
objective ceiling on the same axis.

An orchestration run begins when the controller accepts one Owner objective and
assigns its durable run ID. It spans every controller invocation, subprocess,
resumed task turn, and phase for that objective until the controller records
complete, blocked, cancelled-by-Owner, or superseded-by-a-new-Owner-objective.
Starting another local process does not reset the cumulative envelope. This
packet does not claim to enforce a weekly or cross-run account ceiling; those
signals may advise routing only when separately available and trustworthy.
Creating or superseding an objective requires an explicit Owner action; model
output, controller policy, envelope exhaustion, or a worker result cannot reset
the run. The transition SHALL record old/new run IDs, timestamp, and a digest
of the Owner-authorized transition without retaining the Owner's raw message.

#### Scenario: Usage data is unavailable
- **WHEN** the provider exposes no trustworthy token or remaining-capacity data
- **THEN** the phase reports usage unknown and still enforces the observable
  elapsed-time, call-count, input-byte, and configured-budget ceilings

#### Scenario: A phase reaches its envelope
- **WHEN** any configured ceiling is exhausted
- **THEN** no new automatic call starts and the result names the safe next
  route: smaller scope, an advisory-only right-sized model, or return to the
  Owner

#### Scenario: The cumulative run envelope is exhausted
- **WHEN** aggregate elapsed time, call count, outbound bytes, or configured
  provider spend reaches the run ceiling even though the current phase has room
- **THEN** the run stops before another automatic call and returns the
  remaining work to the Owner

#### Scenario: A cheaper model is available after exhaustion
- **WHEN** an exhausted phase routes a bounded task to a cheaper or otherwise
  different model
- **THEN** its output is advisory only and SHALL NOT satisfy peer convergence,
  architecture critique, cross-review, independent verification, or any other
  gate

### Requirement: Objective high-impact properties trigger pre-mutation peer critique
Every change that affects persistence, permissions, process boundaries, or
verification semantics is FULL by definition and SHALL trigger
architecture/security critique before a mutating worker starts. This trigger
depends only on the affected behavior, not on the packet's self-assigned mode
or gate labels. If critique is unavailable and existing single-pilot rules
permit lifecycle work, the controller SHALL emit a machine-readable
`critique_skipped` disclosure with reason and
`peer_convergence: not_established`; the missing critique SHALL NOT satisfy an
integration or review gate.

#### Scenario: Late review would force redesign
- **WHEN** a plan changes persistence, permissions, process boundaries, or
  verification semantics regardless of its declared mode
- **THEN** the peer sees the bounded plan and delta requirements before any
  mutating worker starts

#### Scenario: Packet omits a peer gate
- **WHEN** objective high-impact properties apply but the packet does not name
  peer convergence as an integration gate
- **THEN** pre-mutation critique is still required

#### Scenario: Critique cannot be obtained
- **WHEN** a supported operational failure prevents the pre-mutation critique
- **THEN** the result records `critique_skipped`, the exact operational reason,
  and `peer_convergence: not_established`


### Requirement: A live equivalent invocation is never duplicated
The controller SHALL derive a request fingerprint from the candidate, bounded
request, model, schema, and relevant configuration. It SHALL persist bounded
invocation identity, process identity/lease, and eligible terminal structured
output. While an equivalent invocation is live, another automatic invocation
SHALL attach to or report the existing call rather than start a duplicate.
Stale identity SHALL be rejected through process-identity and lease checks. An
expired lease without a terminal result SHALL return to the Owner and SHALL
NOT authorize an automatic restart.

#### Scenario: Outer invoker is interrupted
- **WHEN** the shell or agent awaiting a peer call disappears while the bounded
  peer process remains live
- **THEN** a later controller observes the existing invocation and does not
  spend a second call

#### Scenario: Terminal output exists
- **WHEN** the peer reaches a schema-valid terminal result
- **THEN** the result is atomically durable before it is reported to the
  invoker and may be recovered by fingerprint within its freshness bound

#### Scenario: Lease expires without terminal output
- **WHEN** the recorded process identity is absent or mismatched, the lease is
  expired, and no terminal result was durably recorded
- **THEN** the controller reports an indeterminate interrupted call and returns
  to the Owner without automatically spending a replacement call

### Requirement: Durable peer results are bounded, screened, fresh, and out of tree
Invocation state SHALL live in an application-owned local state directory
outside the repository and known synchronized trees. It SHALL never persist
the outbound prompt or source bodies. Before a terminal result body is stored,
a dedicated at-rest content secret screen SHALL pass and the canonical body
SHALL be at most 64 KiB. An ineligible body SHALL leave only its digest,
terminal classification, and non-sensitive reason. Recoverable bodies SHALL
carry original observation time, exact fingerprint, and SHALL expire no later
than 24 hours after observation. Logical expiry is enforced on every read and
controller startup before a body can be returned or satisfy a gate; the first
such access after expiry SHALL delete the body. Physical deletion while
Drydock is not running is not claimed. Expired bounded metadata SHALL NOT
satisfy a current gate. The store is user-writable and SHALL NOT be described
as authenticated or as attestation.

#### Scenario: Peer result contains secret-shaped content
- **WHEN** the terminal structured result matches the at-rest secret screen
- **THEN** the body is not persisted and recovery reports
  `terminal_result_not_persisted` with bounded digest/status metadata

#### Scenario: Recovered result is stale
- **WHEN** a matching terminal result is older than 24 hours
- **THEN** the access deletes its stored body, reports only bounded stale
  metadata with the original observation time, and SHALL NOT satisfy critique,
  convergence, review, or verification

#### Scenario: Worktree is inspected
- **WHEN** durable orchestration state is written or cleaned
- **THEN** no state file exists under the repository or changes its Git
  executable-surface or packet-evidence fingerprint

### Requirement: Oversized review input is refused before provider spend
The controller SHALL compare outbound bytes and the configured review-input
envelope before spawn. An oversized request SHALL NOT be truncated silently or
sent. The result SHALL disclose omitted scope and route to a repository-aware
Owner relay, separately approved snapshot mechanism, or smaller review whose
limitations remain explicit.

#### Scenario: Source bundle fits the legacy absolute cap but not the phase
budget
- **WHEN** a code-review payload is below the parser's absolute safety bound but
  above the configured review-input envelope
- **THEN** the controller refuses before provider spawn and reports
  `input_budget_exceeded`

### Requirement: Proof reuse is candidate- and command-bound
The controller SHALL maintain two distinct, domain-separated v2 digests under
the explicit scheme identifier `drydock-repository-fingerprint-v2`. Both
digests SHALL use exact committed Git-tree paths, modes, types, and blob bytes,
not platform working-tree bytes. Every entry field SHALL be framed by its
unsigned 64-bit big-endian byte length before its bytes are hashed, so arbitrary
blob content, including NUL bytes, cannot impersonate field or entry
boundaries:

- an executable-surface fingerprint over all tracked source, tests,
  dependencies, configuration, generators, hooks, agent instructions, and
  skills that can affect behavior or proof; and
- a packet-evidence fingerprint over an exact allowlist of non-executable
  review-result and verification-record paths.

The packet-evidence allowlist is limited to regular non-symlink files at the
active packet root named `verification.md`,
`claude-architecture-review-round-<positive-integer>.json`, or
`codex-final-verifier.json`. JSON members SHALL pass their dedicated evidence
schema at `specs/packet-evidence.schema.json`. Every other packet path,
including brief, plan, decision log, specs, scripts, configuration, and unknown
names, belongs to the executable surface for invalidation purposes.

The single exact target path `<active-packet-root>/tasks.md` SHALL be
dual-projected. Its raw committed bytes belong to packet-evidence identity. Its
executable projection SHALL preserve every byte except the state byte in a
canonical task marker, which SHALL be normalized to ASCII space. The canonical
marker is a line prefix containing zero or more ASCII spaces or tabs, `-`, zero
or more ASCII spaces or tabs, `[ ]`, `[x]`, or `[X]`, and one or more trailing
ASCII spaces or tabs. Task wording, continuation lines, headings, ordering,
non-state whitespace, added or removed tasks, and noncanonical state markers
remain executable. The protocol is byte-based rather than CommonMark-based.
Task templates and every other packet's tasks file remain fully executable.

Projection SHALL use the committed blob after committed-tree sourcing is
established. A BOM, CR byte, invalid UTF-8, legacy-recognized marker outside the
canonical ASCII grammar, absent exact path, wrong Git type, or case-fold
equivalent conflict SHALL decline projection with an explicit diagnostic and
hash any present task file completely as executable. It SHALL NOT abort
fingerprint computation or silently apply a best-effort normalization.

Checkbox status is lifecycle and governance evidence. It can change Stop-hook,
status, verification, and archive-gate outcomes without changing executable
identity. Unchanged executable identity SHALL NOT be interpreted as unchanged
governance state. Task-file existence remains a packet-governance input, and
task text and ordering remain executable because lifecycle consumers inspect
them.

V1 proof records SHALL NOT satisfy v2 reuse or final acceptance. Reusable and
final proof records SHALL carry and validate the explicit fingerprint scheme
identifier in addition to digest equality.
An allowlisted, schema-valid review summary records a reported result; it does
not authenticate provenance, establish peer agreement, or satisfy a gate by
itself.

Reusable test or verification evidence SHALL bind the executable-surface
fingerprint, exact command, relevant environment fingerprint, terminal status,
and output digest. Reuse SHALL require a clean committed Git tree with no
ordinary untracked files and no ignored code-injection path. A source,
dependency, configuration, hook, generator, loadable file, environment, or
unknown relationship SHALL invalidate every affected proof. No cached result
authorizes effects or replaces an independent verifier. Reuse is an
intermediate-work optimization only.

The fresh proof root SHALL contain exactly the committed regular-file path set,
blob bytes, and executable-mode semantics described by v2 identity. An
`export-ignore`, `export-subst`, gitlink, tracked link, unsupported mode, or
other archive/tree divergence SHALL fail proof materialization.

#### Scenario: Working tree is dirty or contains untracked files
- **WHEN** Git reports any tracked modification or untracked path, including a
  loadable `conftest.py`, `sitecustomize.py`, `.pth`, or untracked, non-ignored
  bytecode artifact
- **THEN** proof reuse is disabled and no prior result is attached to the
  current candidate

#### Scenario: Ignored path can inject or override Python or pytest code
- **WHEN** an ignored path matches `conftest.py`, `sitecustomize.py`,
  `usercustomize.py`, or `*.pth`
- **THEN** proof reuse is disabled even though ordinary Git status omits the
  path

#### Scenario: Ignored bytecode caches exist in the Owner checkout
- **WHEN** ignored `__pycache__` directories or `*.py[cod]` files exist outside
  the proof root
- **THEN** their existence alone does not disable reuse; proof generation and
  reuse validation run in a fresh ephemeral root materialized from the exact
  executable commit, verify that root contains no bytecode before spawn, and
  disable bytecode writing for the command

#### Scenario: Bytecode appears inside the proof root
- **WHEN** `__pycache__` or `*.py[cod]` exists in the fresh proof root before
  the command starts
- **THEN** the root is not proven clean and reuse is disabled; the controller
  does not purge an unexplained file and continue

#### Scenario: Tracked bytecode exists
- **WHEN** the complete tracked tree contains a bytecode artifact that the
  interpreter could load
- **THEN** proof reuse is disabled rather than treating the tree digest as
  proof that source and bytecode are semantically aligned

#### Scenario: Changed relationship is unknown
- **WHEN** the controller cannot prove that a source or environment change is
  irrelevant to a prior command
- **THEN** that proof is invalidated and the command must run again

#### Scenario: Clean checkout bytes differ from committed bytes
- **WHEN** Git reports a clean checkout but platform newline conversion or file
  modes make working-tree bytes differ from the committed tree
- **THEN** v2 identity is computed from the committed tree and blob bytes that
  the fresh proof root materializes, while checkout cleanliness remains a
  separate gate

#### Scenario: Only canonical task status changes
- **WHEN** a committed change modifies only `[ ]`, `[x]`, or `[X]` state bytes
  in the exact target packet task file
- **THEN** executable identity remains stable, packet-evidence identity changes,
  and current lifecycle gates evaluate the new status directly

#### Scenario: Task contract or uncertain task syntax changes
- **WHEN** task wording, ordering, continuation text, non-state whitespace,
  membership, template content, another packet, or noncanonical syntax changes
- **THEN** executable identity changes, or uncertain target syntax declines
  projection and the complete target task file remains executable

### Requirement: Separate Codex processes receive a pinned Git context
The process runner SHALL supply an exact command-scoped
`shell_environment_policy.set` map for every delegated root. The supplied map
SHALL set Git configuration count/key/value fields that mark only the canonical
delegated root as `safe.directory`; null global and system Git configuration;
disable system attributes, optional locks, and terminal prompts; and set one
canonical Git ceiling. The runner SHALL also pin
`shell_environment_policy.inherit="core"` as the Codex-defined mechanism that
excludes unlisted inherited environment variables; the explicit `set` map
alone SHALL NOT be described as sanitizing every possible `GIT_*` variable.
Repository tests establish the requested command-line configuration shape, not
Codex's replace-versus-merge semantics or the membership of `core`; those
remain point-in-time platform properties requiring a live effective-environment
probe.

The runner SHALL NOT mutate Owner, global, system, or repository Git
configuration to establish trust. Its own Git helpers and the proof-identity
Git helpers SHALL independently pass the canonical current root as
command-scoped `safe.directory`, because those helpers deliberately remove
inherited `GIT_*` variables. The injected shell defaults make cooperative
verifier commands usable; they SHALL NOT be described as tamper-resistant
against model-authored code that deliberately replaces its own process
environment.

#### Scenario: Sandbox identity differs from repository owner
- **WHEN** a read-only Codex process runs Git under a sandbox SID different
  from the repository owner's SID
- **THEN** direct Git and Drydock's internal Git helpers operate against only
  the canonical delegated root without a `dubious ownership` failure or a
  global `safe.directory` write

#### Scenario: Owner shell overrides exist
- **WHEN** Owner configuration contains unrelated
  `shell_environment_policy.set` values or the parent environment contains
  hostile `GIT_*` variables
- **THEN** the runner supplies its exact root-bound map and `inherit="core"` as
  command-scoped overrides, while internal helpers independently replace
  inherited Git state with pinned command-scoped configuration
- **AND** whether the effective delegated environment retains an unlisted
  Owner value is reported from a live probe rather than inferred from argv

### Requirement: Test execution follows a targeted-to-full ladder
During mutation, the controller SHALL prefer the smallest checks that cover the
changed behavior. It SHALL freeze a candidate before the full required suite
and SHALL run the complete required suite against the exact final
executable-surface fingerprint. Targeted checks and composed or reused proof MAY
accelerate intermediate fingerprints only. A change to any executable-surface
byte after the full run creates a new fingerprint that SHALL receive its own
complete required-suite execution before final acceptance. Recording the
passing result in an allowlisted packet-evidence path changes only the
packet-evidence fingerprint and SHALL NOT self-invalidate the executable proof.
The final report SHALL disclose the exact executable-surface fingerprint and
an exact packet-evidence-parent fingerprint computed over the allowlisted
evidence set plus raw target task state, excluding the report record being
written. It SHALL NOT claim a self-inclusive evidence digest. The verifier
attests the executable candidate only; it does not attest its own later
completion marker or the user-writable evidence digest.

#### Scenario: Isolated intermediate failure is corrected
- **WHEN** a focused correction produces a new intermediate fingerprint
- **THEN** the affected focused command may run immediately, but that composed
  evidence SHALL NOT replace the full required suite on the final fingerprint

#### Scenario: Passing result is recorded after the final suite
- **WHEN** a commit after the complete suite changes only an allowlisted
  non-executable verification or review-result path, with no type/symlink
  change or executable-surface byte change
- **THEN** final acceptance retains the exact tested executable-surface
  fingerprint and records the new packet-evidence fingerprint

#### Scenario: Read-only verifier audits proof without duplicating tests
- **WHEN** the final full required suite already passed on the exact frozen
  executable fingerprint and the separate verifier has no writable temporary
  directory
- **THEN** the parent runner recomputes the v2 candidate identity and refuses
  to spawn the provider or accept PASS unless `final_suite_acceptance` accepts
  a schema-v2, full-required-suite, passed, non-timeout, exit-zero record for
  that exact executable fingerprint
- **AND** the same bounded record is supplied to the verifier for review of the
  implementation, specification, state binding, and read-only checks without
  rerunning write-requiring test commands inside its permission boundary
- **AND** the result labels the record user-writable, unauthenticated, and
  required but insufficient for PASS; it does not claim that structural
  admission attests execution provenance or replaces the separate verifier

#### Scenario: Final proof is absent, stale, or structurally invalid
- **WHEN** the final verifier receives a v1, intermediate, failed, timed-out,
  non-zero-exit, malformed, or executable-fingerprint-mismatched proof record
- **THEN** the parent runner refuses it before provider spawn and no verifier
  verdict can be accepted

#### Scenario: A packet change can affect governed behavior
- **WHEN** a spec, plan, task contract, agent instruction, skill, configuration,
  source, test, hook, generator, dependency, or non-allowlisted path changes
  after the complete suite
- **THEN** the executable-surface fingerprint changes and final acceptance
  remains unsatisfied until the complete required suite runs on it

### Requirement: Efficiency evidence uses observable facts
Dogfood records SHALL report actual elapsed time, call counts, input bytes,
commands, mode/model routing, and trustworthy provider/account evidence. They
SHALL NOT fabricate token counts or claimed savings. Automatic default
thresholds SHALL remain configurable and uncalibrated until supported by
multiple representative observations.

#### Scenario: Owner reports account-gauge consumption
- **WHEN** the Owner observes a weekly usage change that the controller cannot
  independently authenticate
- **THEN** the observation is labelled Owner-reported and is not converted into
  exact token consumption

### Requirement: Observable efficiency surfaces are not overclaimed
The controller SHALL enforce and report the subprocess calls, request bytes,
elapsed time, configured budgets, and provider/account signals it can directly
observe. It SHALL NOT claim to measure all provider-side reasoning tokens,
context-cache behavior, or nested-worker context ingestion when those surfaces
are unavailable. The orchestrated workflow SHALL allow no more than one active
mutator per worktree, one equivalent peer/reviewer call per request
fingerprint, and one verifier per final candidate unless the Owner explicitly
authorizes a replacement after a terminal failure.

#### Scenario: Worker loads broad internal context
- **WHEN** the provider does not expose nested-worker context ingestion
- **THEN** Drydock reports that cost surface as unobserved rather than claiming
  the phase envelope measured it

#### Scenario: Equivalent reviewer already exists
- **WHEN** a matching reviewer invocation is active or a fresh eligible
  terminal result exists
- **THEN** the controller attaches or recovers it and does not start another
  automatic reviewer
