# Verification

## Change

orchestration-efficiency-hardening

## Automated Checks

- [x] Packet evidence schema and all eight Claude review summaries validated
  with `jsonschema.Draft202012Validator`.
- [x] `python scripts/sdd.py verify orchestration-efficiency-hardening`.
- [x] `git diff --check`.
- [x] Focused controller/evidence tests:
  `python -m pytest adapters/codex/tests/test_orchestrator.py
  adapters/codex/tests/test_orchestration_evidence.py -q
  -p no:cacheprovider` reported 62 passed on Python 3.11 after round-five
  implementation-review remediation.
- [x] Python 3.12 compiled the controller, evidence module, and both focused
  test files with an out-of-tree bytecode cache. Python 3.12 pytest execution
  was unavailable because that interpreter has no pytest installation; this is
  not reported as a passing test run.
- [ ] Full Codex adapter suite after candidate freeze.
- [ ] Legacy suite after candidate freeze.
- [ ] Root/scaffold, hook, bundle, release-version, packet, and diff parity.

## Manual Checks

- [x] Confirmed both automated code-review attempts exceeded the configured $1
  provider ceiling without a verdict.
- [x] Confirmed each result reported `subtype: error_max_budget_usd` but
  incorrectly returned `workflow.action: continue_codex_only`.
- [x] Confirmed the first outer-shell timeout left the one known peer child
  alive until it was deliberately stopped; no duplicate was launched while it
  remained active.
- [x] Sent the pre-implementation brief, plan, and delta spec to Fable 5 as a
  15,824-byte bounded request before any runtime edits.
- [ ] Peer critique of the pre-implementation architecture. The sole automated
  attempt returned no verdict: after 115 seconds it exited
  `error_max_budget_usd` under a $0.50 ceiling. This is operational evidence,
  not review or convergence.
- [x] Owner-relayed Claude Code architecture review inspected exact commit
  `8d4dd5c` read-only and returned `converged: false` with four blockers. The
  findings are faithfully summarized, not verbatim-preserved, in
  `claude-architecture-review-round-1.json`.
- [x] Round-one blocker remediation is present normatively: fail-closed
  availability allowlist, objective critique trigger, advisory-only downgrade,
  final-fingerprint full suite, clean-tree reuse, no-auto-restart leases,
  cumulative run budget, and screened out-of-tree terminal retention.
- [x] Owner-relayed round-two review inspected exact range
  `8d4dd5c..dd4c9a5`, confirmed every round-one closure, and returned
  `converged: false` with two new anchoring blockers. Its findings are
  faithfully summarized in `claude-architecture-review-round-2.json`.
- [x] Round-two remediation partitions executable/evidence fingerprints,
  retargets the exact predecessor requirement, places novel requirements under
  ADDED, scans ignored loadable paths, defines the multi-invocation run,
  removes FULL self-labelling and advisory gate scope, and enforces expiry on
  read/start.
- [x] Owner-relayed round-three review inspected exact range
  `dd4c9a5..d114fb7`, confirmed nine of ten rechecks, and returned
  `converged: false` because ignored bytecode created by the required suite
  made proof reuse unreachable. Its findings are faithfully summarized in
  `claude-architecture-review-round-3.json`.
- [x] Round-three remediation separates ignored code-injection hazards from
  neutralized bytecode caches, uses a fresh bytecode-free proof root, defines
  the non-self-referential evidence fingerprint, explicitly supersedes the
  remaining predecessor scenario, defines zero provider cost and unknown-cost
  behavior, supplies the evidence schema, and requires explicit Owner action
  to reset a run.
- [x] Packet evidence is explicitly proof-neutral but remains gate-relevant:
  `verification.md` does not invalidate executable proof, while its parsed
  Result and checklist state still affect archive readiness.
- [x] Owner-relayed round-four review inspected exact range
  `d114fb7..9d7ff0a`, rechecked all six round-three changes from the packet, and
  returned `converged: true` with no blockers. Its findings are faithfully
  summarized in `claude-architecture-review-round-4.json`.
- [x] Round-four clarity follow-up narrows the requirement body to ignored
  code-injection paths, identifies the dirty-tree bytecode case as untracked
  and non-ignored, and states that schema-valid summaries do not establish peer
  agreement or satisfy gates.
- [x] The fixed-root broad implementation worker was stopped after eight
  minutes with zero file writes and no result; its process tree was confirmed
  absent and its worktree remained unchanged.
- [x] The reshaped three-file fail-closed worker returned after about seven and
  a half minutes with 37 worker-reported passing tests and exact usage evidence:
  914,677 input tokens, 806,144 cached input tokens, 20,985 output tokens, and
  13,545 reasoning-output tokens. The runner classified the result
  `ignored_artifacts` because pytest created `.pytest_cache` and bytecode
  caches, so the worker claim was not trusted.
- [x] The pilot independently reran that focused three-file result with
  bytecode writes and pytest caching disabled: 37 passed. After integrating the
  remaining bounded controller/state work, the combined focused suite reports
  57 passed.
- [x] Implementation now includes the fail-closed availability allowlist,
  input preflight, objective-property critique trigger, cumulative envelopes,
  single-flight and bounded terminal recovery, executable/evidence
  fingerprints, fresh proof roots, intermediate proof reuse, and final-suite
  exact-fingerprint binding.
- [x] Owner-relayed implementation review inspected exact range
  `a10faf3..0444a0f`, reproduced 57 focused tests, confirmed the principal
  mechanisms, and returned `converged: false` because a crash-stale ledger
  lock permanently blocked run mutation. Its findings are faithfully
  summarized in `claude-architecture-review-round-5.json`; the filename
  follows the packet's narrow evidence allowlist, while the content explicitly
  identifies this as implementation cross-review.
- [x] Round-five remediation serializes lock recovery with an operating-system
  advisory lock, recovers absent, mismatched, unreadable, or expired holder
  records, preserves refusal for a live holder, exposes tested `close-run`
  lifecycle closure, keys proof by scope, emits a uniform critique-gate block,
  documents the external mutation interlock, and pins tar extraction behavior
  where supported.
- [x] Owner-relayed implementation re-review inspected exact clean HEAD
  `1f2969c720f2ee6e023b1a77105eafa345bf5c07` and range
  `0444a0f..1f2969c`, independently reproduced 62 focused passing tests,
  directly probed stale and concurrent lock behavior, close-run validation,
  scope-bound proof identity, critique-gate reporting, and tar extraction, and
  returned `converged: true` with no blockers. Its findings are faithfully
  summarized in `claude-architecture-review-round-6.json`.
- [x] Pre-freeze inspection found two proof-identity defects not covered by the
  round-six implementation range: task completion changed the executable
  fingerprint after its own proof, and clean Windows checkout bytes/modes could
  differ from the committed bytes materialized by `proof-run`.
- [x] Automated Opus review rejected the first task dual-projection design with
  four specification blockers. Its terminal result is summarized in
  `claude-architecture-review-round-7.json`. A revised second automated call
  timed out at 150 seconds; Windows Job Object cleanup, direct-process absence,
  and drained output pipes were confirmed, but no verdict or convergence was
  inferred.
- [x] Owner-relayed Claude review inspected exact clean HEAD `594dad7`,
  reproduced both defects, found 78 of 469 tracked paths with clean checkout
  bytes differing from committed blobs, audited every task-state consumer, and
  returned `converged: true` on the blob-sourced v2 design. Its findings and
  required implementation points are faithfully summarized in
  `claude-architecture-review-round-8.json`.
- [x] V2 implementation sources exact committed Git tree/blob bytes, labels and
  domain-separates both digests, rejects v1 records structurally, dual-projects
  only the exact target packet task state, falls back to executable-only task
  hashing with an explicit diagnostic, and checks proof archive paths, bytes,
  and executable modes against the committed tree.
- [x] A trusted `apply_patch` attempt was denied mid-task after the
  host-supplied `PLUGIN_ROOT` contract disappeared. The inline verifier refused
  before runtime execution. This is recorded as a separate Codex
  host/bootstrap environment defect; no repository/cache/`PATH` root discovery
  or other fail-open fallback was added.
- [x] On continuation, a same-content `apply_patch` probe against
  `docs/AI_OPERATOR_GUIDE.md` succeeded. Its normalized worktree and HEAD blob
  IDs both remained `9e6d339f7e7b3210100473a67fe71bb7cb6eb394`, and no probe
  content diff remained before the requested edits.
- [x] Focused controller/evidence suite after the v2 correction:
  `python -m pytest adapters/codex/tests/test_orchestrator.py
  adapters/codex/tests/test_orchestration_evidence.py -q
  -p no:cacheprovider` reported 67 passed.
- [x] A controller-side audit before freeze found that delimiter-only v2 tree
  serialization let arbitrary NUL-bearing blob bytes impersonate later entry
  boundaries without a SHA-256 collision. The implementation now length-frames
  every path, type, mode, and body field. Its adversarial regression first
  reproduces the old structural collision and then proves the framed inputs
  differ. The same remediation adds direct v1 final-refusal, repository-level
  projection-decline/fallback, exact task-scope, task-contract mutation, tracked
  link, and gitlink rejection coverage.
- [x] Focused controller/evidence suite after the framing remediation:
  `python -m pytest adapters/codex/tests/test_orchestrator.py
  adapters/codex/tests/test_orchestration_evidence.py -q
  -p no:cacheprovider` reported 82 passed. Packet artifact verification passed
  with 25 complete and 4 pending tasks, and range diff-check passed.
- [x] Owner-relayed Claude implementation re-review inspected exact clean HEAD
  `dee2ebeac43ae0b7a7b72083d88f87484eed3428` and range
  `68c8bbb..dee2ebe`, independently reproduced the old structural collision and
  framed separation, direct v1 final refusal, projection decline/fallback,
  exact task scope, contract mutations, archive divergence, 82 focused tests,
  packet verification, range diff-check, and all eight existing evidence-schema
  validations. It returned `converged: true` with no blockers or required
  changes. Four fail-closed, currently unreachable consistency/diagnostic gaps
  and the carried risks are preserved in
  `claude-architecture-review-round-9.json`; they are not promoted into proof or
  separate final verification.
- [x] Candidate freeze: clean committed HEAD
  `239f42e57c4a5b96d6f11408ac319f3ab451ceec` produced v2 executable
  fingerprint
  `b2bff34466e5bde7457e5b3446e087d584bee2388ea98561330344d1d8287b6f`.
  It exactly matches the pre-evidence fingerprint at reviewed HEAD `dee2ebe`;
  round-9 evidence, verification text, and canonical task-state transitions
  changed only packet-evidence identity. Reuse eligibility was true with no
  tracked bytecode, ignored code-injection path, or invalid packet evidence.
- [ ] Independent review of the frozen implementation.

## Documentation Updates

- [x] Operator guidance updated.
- [ ] Project context updated if the durable defaults change.
- [x] Delta spec written before runtime code.

## Result

V2 PROOF-IDENTITY ARCHITECTURE CONVERGED; THE PRE-FREEZE STRUCTURAL
SERIALIZATION FINDING IS REMEDIATED, FOCUSED TESTS PASS, AND IMPLEMENTATION
CROSS-REVIEW CONVERGED. EXECUTABLE CANDIDATE
`b2bff34466e5bde7457e5b3446e087d584bee2388ea98561330344d1d8287b6f`
IS FROZEN; FULL SUITES AND SEPARATE VERIFICATION REMAIN PENDING. The
implementation does not claim
fixed-root mutation containment:
after the measured runner failures above, the pilot edited the scoped Owner
checkout directly. Remaining disclosed risks include stacked unsynced deltas,
pre-mutation objective classification remains a judgment, oversized or
secret-bearing terminal output can require a new Owner-approved call, evidence
state is user-writable rather than attested, proof-root test behavior may differ
from a Git checkout, and default envelopes remain uncalibrated.
