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
- [x] Full Codex adapter suite after candidate freeze.
- [x] Legacy suite after candidate freeze.
- [x] Root/scaffold, hook, bundle, release-version, packet, and diff parity.

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
- [x] Final full-suite proof ran from fresh committed-tree materialization at
  exact clean HEAD `4caa98812e5774c48bdd78451abaf43d0a5a4c10`, whose v2
  executable fingerprint remained
  `b2bff34466e5bde7457e5b3446e087d584bee2388ea98561330344d1d8287b6f`.
  One sequential command chain ran the legacy suite, full Codex adapter suite,
  root/scaffold sync check, scaffold-bundle parity, generated-hook parity,
  release-version parity, and packet verification. The external proof record
  reports `terminal_status: passed`, exit code 0, `timed_out: false`,
  180.453 seconds elapsed, environment digest
  `2f903bc2c7a4829eb1c95cc7c1356cd2daa970ada729eb8e936f0ae9c31fa75b`,
  and output digest
  `d45d67fb77ed0a06383c04d64f852d3ca1fafd389c207d1996d08f4087a15057`.
  The record is user-writable identity evidence, not attestation; the outer
  shell wrapper stopped observing the surviving child, so individual current
  test counts are not reconstructed from the digest.
- [x] The first separate read-only verifier attempt after the full-suite
  checkpoint is not accepted as verification. The runner bound its schema to
  actual evidence HEAD
  `6f281a3eff9c4d131d7a35bf1b1b2dd95d628de4`, but the pilot's human-authored
  request accidentally named a different hash with the same short prefix.
  The child process tree ended, while the outer orchestration wrapper did not
  surface a recoverable structured verdict. Either defect is sufficient to
  withhold PASS. No absence or process exit was interpreted as a result, and
  no automatic paid retry was launched.
- [x] After explicit Owner approval, a corrected bounded verifier removed the
  manually duplicated HEAD, used only runner-owned state binding, and ended
  after about four minutes without changing the repository. Its result is also
  not accepted: the pilot's durable-capture wrapper used the unsupported
  Windows PowerShell 5.1 parameter `New-Item -LiteralPath`, so the output
  directory was never created and the ephemeral structured verdict was not
  recoverable after process exit. A later local no-model probe with
  `New-Item -Path`, hidden-process stdout redirection, and an explicit file
  read proved the corrected capture mechanism before any further paid call.
  No process exit or missing output was interpreted as PASS, and no third
  verifier was launched without renewed Owner authorization.
- [x] The renewed, preflighted verifier preserved its complete 8,275-byte
  runner result (SHA-256
  `9acd09d141fd0b93dc9979d4fd420246a4f6d807880eea27507a79367e18f427`)
  with zero wrapper stderr. The runner bound exact HEAD
  `8118a7fa7a7ae06b1241a70d848019694a78922f` and working-tree fingerprint
  `e0661bb8990bec2233afd53c8c48e8b1b6a8ede908e72a39cca70a877eafb6b3`,
  returned process exit 0 without timeout, proved the tree unchanged and the
  Windows Job Object boundary closed, and produced a schema-valid `BLOCKED`
  verdict. It positively checked frozen ancestry and executable identity,
  committed-tree equality across 472 paths, source/test/spec agreement, packet
  state, all nine peer-evidence schemas, and diff checks. It blocked because
  the read-only sandbox denied the external proof-store path and could not
  allocate pytest temporary files. The exact blocking summary is preserved in
  `codex-final-verifier.json`; no implementation failure or PASS is inferred.
- [x] After Owner-approved evidence-delivery remediation, a further verifier
  received the exact 1,585-byte proof record in-band after local
  `final_suite_acceptance` returned accepted. Its preflight proved the exact
  PowerShell file/capture path, zero wrapper parse errors, a clean tree, and no
  active verifier. The runner preserved 5,179 bytes of output (SHA-256
  `7153936680b7f4193d67b3bf5239bcd611e4bfe8dbfe09120260a149d7d73c53`)
  with zero wrapper stderr, but returned `timed_out: true`, process exit 1,
  `parse_error: verifier emitted no structured verdict file`, and `ok: false`.
  Its before/after binding matched HEAD
  `9271a22dd7e119746745868e640480947353a180` and working-tree fingerprint
  `c1ddb492129ad4d5e1284ea1e0f765fe92bd0678751429ab8a520c47d174d09a`;
  the tree stayed unchanged. The captured tool tail shows ordinary Git failed
  under the `CodexSandboxOffline` SID with `dubious ownership` until the model
  injected `safe.directory`; a later direct committed-tree/archive probe
  matched all 473 paths and mode/bytes. No missing structured verdict or
  partial positive check is interpreted as PASS. The verifier runner must make
  its fixed read-only Git context usable before another paid attempt.
- [x] Claude's focused review of
  `b9e9da77e68f330c44b998e88b645b5b5251b6f0..fe2ffd004da1a04bc4a43101a726f31f257f0632`
  reproduced 132 focused passes, packet verification, diff cleanliness, and
  all nine prior peer-evidence schema validations. It returned non-converged
  on two claim/mechanism gaps: proof review was instruction-only, and the
  subprocess-environment text asserted unproven Codex merge behavior. The
  exact review is recorded as `claude-architecture-review-round-10.json`; no
  candidate freeze or PASS is inferred.
- [x] A native-Windows effective-environment probe ran against
  `codex-cli 0.146.0-alpha.3.1` with a simulated lower-priority Owner `set`
  table and, in the final run, parent `GIT_DIR`, `GIT_OBJECT_DIRECTORY`, and
  `DRYDOCK_PARENT_UNLISTED` poison. All simulated Owner/parent poison was absent
  from the tool child, and every requested runner value was present. Codex also
  appended `GIT_CONFIG_KEY_1=safe.directory` with the equivalent native
  Windows root and changed effective `GIT_CONFIG_COUNT` from requested `1` to
  `2`. The two detailed 530-byte results were identical at SHA-256
  `9b1fd50eed61c8e58bc1c58f8f1a9e9401b06c5129369a64e6ea8c1e79e83a9c`.
  The evidence proves only this build and lower-priority CLI layering, not an
  actual Owner config file or another Codex version. One intervening PowerShell
  wrapper attempt failed before `thread.started` because PowerShell 5.1 removed
  TOML double quotes and Codex rejected `shell_environment_policy.set` as a
  string rather than a map; the corrected wrapper used TOML literal strings.
  No result is inferred from the failed wrapper.
- [x] The verifier parent now recomputes v2 candidate identity and treats
  `final_suite_acceptance` as a pre-spawn gate. The first targeted regression
  run exposed five valid-fixture refusals because the Windows test repository
  inherited Owner `core.autocrlf` during setup while proof Git deliberately
  nulled global config. The fixture now pins local `core.autocrlf=false`; the
  corrected targeted run passed 17 tests, including eleven invalid proof
  shapes and a dirty candidate refused before provider spawn. This is focused
  implementation evidence only; re-review and a replacement frozen full suite
  remain pending.
- [x] The complete focused orchestration set passed after the remediation:
  `147 passed in 99.86s` for `test_process_runner.py`,
  `test_orchestrator.py`, and `test_orchestration_evidence.py`, with
  `PYTHONDONTWRITEBYTECODE=1` and pytest cache disabled. No adapter/legacy/parity
  full suite was run.
- [x] Claude's focused re-review of
  `fe2ffd004da1a04bc4a43101a726f31f257f0632..3df92236365b51249e38fa5b4ae039ab49489119`
  reproduced 147 focused passes, packet/diff/schema checks, and returned
  `converged: true` with no blocking concern. It confirmed both round-ten
  blockers closed by mechanism. The exact result is recorded as
  `claude-architecture-review-round-11.json`; it does not authenticate itself,
  freeze the candidate, or satisfy final verification.
- [x] The one non-blocking round-eleven required change is remediated:
  `EvidenceError` from candidate fingerprinting is converted to `RunnerError`,
  so malformed `--packet-root` input returns structured `{ok:false,
  stage:"blocked"}` instead of a traceback. A focused CLI regression plus the
  proof/verifier set passed `21 passed`; it also proves the fake provider log
  is never created. The complete focused orchestration set then passed
  `148 passed in 101.99s`; no adapter/legacy/parity full suite was run.
- [x] Claude's narrow review of
  `3df92236365b51249e38fa5b4ae039ab49489119..74ca3f80dfc6c04f159b57b5c706c4ece0569798`
  reproduced `21 passed` with 44 deselected, packet verification at 38
  complete/3 pending, diff cleanliness, and all eleven prior peer-evidence
  schema validations. It returned `converged: true`, no blocker, no gap, and no
  required change. The exact result is recorded as
  `claude-architecture-review-round-12.json`; it does not authenticate itself,
  freeze the candidate, or satisfy final verification.
- [x] Replacement candidate freeze: exact clean reviewed HEAD
  `1842db937a40891b553f54c96c3e060f38b9941b` produced v2 executable
  fingerprint
  `23d7b23c99aee8e3de5c79e7a2eeb2428113671f6c7b1ebd0af460dec6fe1abf`
  and non-self-inclusive packet-evidence-parent fingerprint
  `2c7322779510b38671d4ea03bcfda7a293accfc6bb853426a6d3fbcee6712419`,
  computed with
  `sdd-plus/changes/orchestration-efficiency-hardening/verification.md`
  explicitly excluded. Reuse eligibility was true, canonical active-task
  projection was applied, and no tracked bytecode, ignored code-injection path,
  or invalid packet evidence was present. This freeze does not reuse the prior
  full-suite proof; one replacement full-required-suite run remains pending.
- [ ] Independent review of the frozen implementation.

## Documentation Updates

- [x] Operator guidance updated.
- [ ] Project context updated if the durable defaults change.
- [x] Delta spec written before runtime code.

## Result

ROUND-TEN VERIFIER-REMEDIATION REVIEW IS NON-CONVERGED. THE TWO BLOCKERS ARE
IMPLEMENTED LOCALLY BUT HAVE NOT RECEIVED RE-REVIEW: FINAL-PROOF ADMISSION IS
NOW A PARENT-RUNNER PRE-SPAWN GATE, AND EFFECTIVE CHILD-ENVIRONMENT CLAIMS ARE
LIMITED TO REQUESTED CONFIGURATION PLUS POINT-IN-TIME LIVE EVIDENCE. THE LIVE
PROBE ALSO PROVED CODEX APPENDS A SECOND EQUIVALENT `safe.directory`, SO THE
RESULT REPORTS REQUESTED RATHER THAN ACHIEVED ENVIRONMENT. THE PRIOR
FULL-REQUIRED-SUITE PROOF DOES NOT BIND THESE EXECUTABLE CHANGES. NO CURRENT
CANDIDATE IS FROZEN, NO REPLACEMENT FULL SUITE HAS RUN, AND SEPARATE
VERIFICATION REMAINS BLOCKED UNTIL RE-REVIEW CONVERGES. The implementation
does not claim fixed-root mutation containment:
after the measured runner failures above, the pilot edited the scoped Owner
checkout directly. Remaining disclosed risks include stacked unsynced deltas,
pre-mutation objective classification remains a judgment, oversized or
secret-bearing terminal output can require a new Owner-approved call, evidence
state is user-writable rather than attested, proof-root test behavior may differ
from a Git checkout, and default envelopes remain uncalibrated.
