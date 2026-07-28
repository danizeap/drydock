# Verification

## Change

orchestration-efficiency-hardening

## Automated Checks

- [x] Packet evidence schema and all four Claude review summaries validated
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
- [ ] Owner-relayed implementation re-review of the remediation commit.
- [ ] Independent review of the frozen implementation.

## Documentation Updates

- [x] Operator guidance updated.
- [ ] Project context updated if the durable defaults change.
- [x] Delta spec written before runtime code.

## Result

ARCHITECTURE CONVERGED AND ROUND-FIVE IMPLEMENTATION-REVIEW REMEDIATION IS
FOCUSED-TEST GREEN; IMPLEMENTATION RE-REVIEW, CANDIDATE FREEZE, FULL SUITES,
AND SEPARATE VERIFICATION REMAIN PENDING. The implementation does not claim
fixed-root mutation containment:
after the measured runner failures above, the pilot edited the scoped Owner
checkout directly. Remaining disclosed risks include stacked unsynced deltas,
pre-mutation objective classification remains a judgment, oversized or
secret-bearing terminal output can require a new Owner-approved call, evidence
state is user-writable rather than attested, proof-root test behavior may differ
from a Git checkout, and default envelopes remain uncalibrated.
