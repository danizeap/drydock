# Spec Delta: orchestration-efficiency-hardening

Capability: codex-host-orchestration

This delta changes orchestration efficiency mechanisms. It does not weaken
packet approval, peer-convergence truthfulness, independent verification,
LaunchGuardian, hook, integration, or release gates.

## ADDED Requirements

### Requirement: Every expensive phase and the whole run have explicit resource envelopes
The controller SHALL bind each plan-peer, mutation, cross-review, verification,
and integration phase to a configured envelope containing elapsed-time,
model-call, outbound-input-byte, and provider-budget ceilings. The controller
SHALL also enforce cumulative ceilings over the entire run so phase limits
cannot multiply beyond the Owner's run boundary. It SHALL record actual
observed values and SHALL represent unavailable token or account usage as
unknown. Exhaustion SHALL produce a structured stop or advisory-reroute
decision and SHALL NOT create a PASS or convergence.

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

## MODIFIED Requirements

### Requirement: Claude is an optional, bounded, structured peer
This MODIFIED requirement supersedes the broader failure-workflow wording under
the same requirement in `codex-host-mvp` and `peer-unavailable-governance`.
Their bounded tool surface, safe mode, strict MCP, secret/input guards, schema,
timeout, cleanup, and no-convergence claims remain unchanged.

Only this explicitly enumerated allowlist of benign availability failures MAY
enter the single-pilot workflow: authentication unavailable before spawn, an
exact supported rate-limit marker, a controller timeout with bounded cleanup,
or an ordinary non-zero process exit that carries no structured provider
subtype and is proven to have consumed zero provider cost. A budget ceiling,
policy/refusal/context-limit abort, malformed output,
model mismatch, missing model/cost proof, unknown structured subtype, unmapped
stage, or other contract/control violation SHALL return to the Owner and SHALL
NOT authorize automatic continuation. The default for every unrecognized value
is `return_to_owner`.

For this requirement, "provider cost is proven zero" means a successfully
parsed top-level CLI envelope for the requested model contains a finite numeric
`total_cost_usd` equal to exactly zero. A missing, malformed, negative, or
unavailable cost field is unknown and never proves zero.

#### Scenario: Claude becomes unavailable mid-workflow
- **WHEN** one of the four allowlisted benign availability failures prevents a
  peer round
- **THEN** Drydock may remain the Codex-hosted governor in machine-readable
  single-pilot mode while reporting `peer_convergence: not_established`

#### Scenario: Claude times out or its process fails
This scenario explicitly supersedes the scenario with the same name in
`peer-unavailable-governance`.

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
