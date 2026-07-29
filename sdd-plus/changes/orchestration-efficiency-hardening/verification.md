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
- [x] One replacement `full_required_suite` run executed from fresh
  committed-tree materialization at exact clean proof HEAD
  `2188580c29091b202f1509c8b9dfa07ec2bba399`. Its v2 executable fingerprint
  remained
  `23d7b23c99aee8e3de5c79e7a2eeb2428113671f6c7b1ebd0af460dec6fe1abf`,
  and the controller persisted schema-v2 proof record
  `1642db8d51a0c67fcb8279b15287aa22301e8154cc0bc1a4adfec43235ce56fc.json`.
  Exact results were: legacy `548 passed, 6 skipped`; Codex adapter
  `314 passed, 2 skipped`; root/scaffold sync `11` pairs identical;
  scaffold bundle matched source; hook runtime and definition matched source;
  all release-version locations agreed at `0.12.1` with a changelog entry; and
  packet verification reported `38 complete, 3 pending`. Every step returned
  zero. The proof record reports `terminal_status: passed`, exit code `0`,
  `timed_out: false`, 184.719 seconds elapsed, environment digest
  `593a134a4358db13ac8bb6d74cfc001f52c53c1785ceefd4dfe519d25f1501b4`,
  and output digest
  `acbe16162e01aae63088e093b60619f918eaa612c091cacf4475204311dda853`.
  Local `final_suite_acceptance` returned accepted for the current clean
  candidate while retaining `authenticated: false` and
  `provenance_attested: false`. The outer controller process exited zero but
  its captured stdout was empty; no result is inferred from that absence.
  Counts come from the durable 3,401-byte suite summary (SHA-256
  `292470fa45cf3f9415d7d14b21a671e930ac152c9841af8d76e507395352a071`),
  and proof acceptance from the separately read persisted record.
- [x] Post-proof governance-state checkpoint: exact clean HEAD
  `42b8571286e35ab45749de8e92fdb59b1cf9930b` retained v2 executable
  fingerprint
  `23d7b23c99aee8e3de5c79e7a2eeb2428113671f6c7b1ebd0af460dec6fe1abf`
  while the non-self-inclusive packet-evidence-parent fingerprint became
  `907e9720b73316d70d8ceddb24523542fc417170e3a7f64491156d5d51b158ff`
  after the replacement-suite task was checked complete. The active packet
  task projection remained canonical, reuse eligibility remained true, and no
  tracked bytecode, ignored code-injection path, or invalid packet evidence
  was present. This is the expected separation between stable executable
  identity and changed governance evidence.
- [x] Final separate-verifier attempt at exact clean HEAD
  `09bdee5d75c337ee9996127294ed5e389a0588d6` returned a schema-valid
  model verdict of `FAIL`; the packet records it fail-closed as `BLOCKED`.
  The parent runner returned `ok: false`, `stage: complete`, exit code `0`,
  `timed_out: false`, and `parse_error: null`. Proof admission was accepted,
  the before/after HEAD and working-tree fingerprint
  `95cbb426f0fb03f9b5a399ca93b696d33fe15d60aa3e2be61d4b6b6ceedd31a5`
  matched, and both `tree_unchanged` and `candidate_unchanged` were true.
  Positive inspection reproduced both requested packet fingerprints, but the
  verifier also reproduced a real sandbox-SID failure: the internal
  `git cat-file --batch` call in `_git_tree_entries` omitted the
  command-scoped `safe.directory` override while its environment removed
  inherited Git configuration. The corresponding regression covered `_git`
  but not this internal subprocess. The verifier additionally noted that the
  exact suite-count summary body is not committed, so it did not independently
  infer the recorded counts. The exact gate result is preserved in
  `codex-final-verifier.json`; no PASS or final verification is inferred.
- [x] Internal Git-helper remediation: `_git_arguments` now constructs the
  canonical root-scoped `safe.directory` argv for both ordinary Git calls and
  the separate `git cat-file --batch` object reader. A new regression invokes
  `repository_fingerprints` through the actual batch subprocess under a hostile
  inherited `GIT_OBJECT_DIRECTORY` and asserts the canonical argv, resolved
  cwd, and scrubbed Git environment. The two Git-trust selections passed
  (`2 passed, 39 deselected`) and the focused orchestration/evidence set passed
  (`84 passed`). A direct point-in-time native-Windows probe then ran the
  fingerprint command through Codex's `:read-only` sandbox profile with the
  absolute Python 3.11 interpreter; it exited `0` and completed the internal
  object read without `dubious ownership`. It reported `clean: false` because
  this remediation was still uncommitted, so the probe is mechanism evidence,
  not a candidate freeze or reusable full-suite proof.
- [x] Bounded Opus 5 implementation review of exact supplied diff
  `5ee31b05d121b74920c996a20907544c87a70dfa..385cb405c6c2fa6dbf610a02241b5e4886f439bf`
  converged with no blocker. The one-round call used 13,587 outbound bytes,
  cost $0.464283 against a $1 ceiling, and observed the requested
  `claude-opus-5` model plus the CLI's Haiku helper. Because the peer received
  a text diff rather than repository tools, it explicitly did not authenticate
  HEAD or range exclusivity. Repository-side checks confirmed the exact HEAD,
  five-file range, both proof-identity Git subprocess call sites, and the
  unchanged `env=_git_environment()` keyword. The peer's nonblocking test
  findings were implemented before freeze: the batch regression now poisons
  the related object/worktree Git-variable family, asserts the exact pinned
  `GIT_*` key set, drops the unrelated reuse-eligibility assertion, and the
  argv helper no longer repeats path resolution. Focused results remained
  `2 passed, 39 deselected` and `84 passed`. These post-review executable/test
  changes still require a narrow follow-up peer check.
- [x] The second and final bounded Opus 5 review of
  `385cb405c6c2fa6dbf610a02241b5e4886f439bf..c0dcacbebd151350b408014520276400c975ee56`
  converged with no blocker. It used 13,173 outbound bytes and cost $0.4149295
  against the second $1 call ceiling; the two-call successor run stayed below
  its phase envelope at 26,760 bytes, 284.13 seconds of peer execution, and
  $0.8792125 observed provider cost. Repository-side source checks closed the
  text-only peer's remaining uncertainty: `_git_arguments` has exactly two
  callers and both pass `_resolved_git_path` output; the batch subprocess uses
  that resolved value and retains `env=_git_environment()`; and
  `_git_environment()` removes every inherited key with a case-insensitive
  `GIT_` prefix before adding only the pinned keys. A focused regression now
  also proves a missing repository path raises the structured `EvidenceError`.
  Final focused results were `3 passed, 39 deselected` for the Git-trust
  selection and `85 passed` for the orchestration/evidence set. Round 14 is
  recorded as peer evidence only; it does not freeze the candidate or satisfy
  final verification.
- [x] Final Git-trust remediation freeze: exact clean reviewed HEAD
  `2b8c0de58b700d526bb9d742c065ece130bc64b3` produced v2 executable
  fingerprint
  `b0f6cff44dfae8db561149ec9bf0f1b45d2479a570000076baefcc3547c981d6`
  and non-self-inclusive packet-evidence-parent fingerprint
  `f084f6f6a2cbea66fd31e255e98edfdc9000d2c2dddb16bb7d79ee92c65d2a7d`,
  computed with this `verification.md` excluded. Reuse eligibility was true,
  canonical active-task projection was applied, and no tracked bytecode,
  ignored code-injection path, or invalid packet evidence was present. The
  earlier proof for executable fingerprint `23d7b23c...1abf` is not reusable;
  a new full-required-suite run remains pending.
- [x] One new `full_required_suite` run executed from fresh committed-tree
  materialization at exact clean proof HEAD
  `974d51ed376e23095b05a5b16504e040680f8d74`. Its v2 executable fingerprint
  was
  `b0f6cff44dfae8db561149ec9bf0f1b45d2479a570000076baefcc3547c981d6`,
  and the controller persisted schema-v2 proof record
  `9f61e8fc3cd897b91f1c3230e190222b663c86f437468f4d5d35f52d4df0bc91.json`.
  Exact results were: legacy `548 passed, 6 skipped in 44.30s`; Codex adapter
  `316 passed, 2 skipped in 130.86s`; root/scaffold sync `11` pairs identical;
  scaffold bundle matched source; hook runtime and definition matched source;
  all release-version locations agreed at `0.12.1` with a changelog entry; and
  packet verification reported `41 complete, 3 pending`. Every step returned
  zero. The proof record reports `terminal_status: passed`, exit code `0`,
  `timed_out: false`, 181.359 seconds elapsed, environment digest
  `e61fe339080aa5bb6c0cc3db60fbbc07d850184fc99c4e1136f78530ebb5eb22`,
  and output digest
  `213c997080da544c43af14f458448a3fce762c2662ea1a8d5961c3cf67818053`.
  The durable 3,401-byte suite summary has SHA-256
  `532f2db4c6fd0493f6a774bd26202505f718d132fbf268e28e9537d384c27026`;
  appending the wrapper's native-Windows CRLF produces the proof record's exact
  output digest. The 2,567-byte proof record itself has SHA-256
  `d274f6760d5aa8ebcdef95df5ad08c9469d705ca141a399943f140931fec58e8`.
  Local `final_suite_acceptance` returned accepted for the current clean
  candidate while retaining `authenticated: false` and
  `provenance_attested: false`. Counts come from the separately read durable
  summary, not from process exit alone.
- [x] Post-proof governance-state checkpoint: exact clean HEAD
  `9b921ed198fe3e8302ce3c0410d12dd647d31742` retained v2 executable
  fingerprint
  `b0f6cff44dfae8db561149ec9bf0f1b45d2479a570000076baefcc3547c981d6`
  while the non-self-inclusive packet-evidence-parent fingerprint became
  `855d176c137aa5774f94387c295bc223d6fcfd007cc348cbabd6f4c7c2888918`
  after the new full-suite task was checked complete. Canonical task
  projection and reuse eligibility remained true, with no tracked bytecode,
  ignored code-injection path, or invalid packet evidence.
- [x] Final separate verification passed at exact clean HEAD
  `f307a7a60c3aaabf17890ab453b2e517064f4f91` and working-tree fingerprint
  `6b9e8c8ab56f5783184be6c0270d007f1cb7b117549a631135ff9cb1cfb1bfd4`.
  The parent runner returned `ok: true`, `stage: complete`, exit code `0`,
  `timed_out: false`, and `parse_error: null`; proof admission was accepted,
  and both `tree_unchanged` and `candidate_unchanged` were true. The verifier
  positively ran `repository_fingerprints` under the actual read-only sandbox
  identity with the hostile Git-variable family and observed no
  `dubious ownership` failure. It confirmed the two shared, root-pinned Git
  subprocess paths; exact scrubbed `GIT_*` set; structured resolution failure;
  v2/tree/projection/archive/admission invariants; schema-valid rounds 13/14;
  clean executable fingerprint
  `b0f6cff44dfae8db561149ec9bf0f1b45d2479a570000076baefcc3547c981d6`;
  and verification-excluded packet-evidence-parent fingerprint
  `855d176c137aa5774f94387c295bc223d6fcfd007cc348cbabd6f4c7c2888918`.
  It could not read the external suite-summary file under its host-file
  boundary, so it explicitly did not independently confirm that file's counts
  or digest. This is retained as a gap rather than rewritten as positive
  evidence. The exact schema-valid PASS summary is recorded in
  `codex-final-verifier.json`; the runner declares
  `epistemic_independence: false`.
- [x] Final post-verdict governance-state checkpoint: exact clean HEAD
  `4bccd1312c561c02f2eda7bb752fc4586a8319a5` retained v2 executable
  fingerprint
  `b0f6cff44dfae8db561149ec9bf0f1b45d2479a570000076baefcc3547c981d6`
  while the non-self-inclusive packet-evidence-parent fingerprint became
  `72842e7ce8b8b53947726e539514b81bb7200e135268c82eab8b108897ce4c99`
  after the final task checkboxes and PASS evidence were committed. Canonical
  task projection and reuse eligibility remained true, with no tracked
  bytecode, ignored code-injection path, or invalid packet evidence. This
  lifecycle-evidence transition does not rewrite the verifier's earlier exact
  state binding or claim that packet evidence authenticates itself.

## Documentation Updates

- [x] Operator guidance updated.
- [x] Project context update not required; this packet did not change the
  project purpose, stack, or durable Owner-level defaults.
- [x] Delta spec written before runtime code.

## Revision 1 Result (Superseded By Active Plan Revision 2)

FINAL SEPARATE VERIFICATION PASSED. THE PREVIOUS SANDBOX-SID
`git cat-file --batch` BLOCKER IS POSITIVELY CLOSED, THE NEW
EXACT-FINGERPRINT FULL REQUIRED SUITE PASSED, AND THE RUNNER CONFIRMED AN
UNCHANGED CLEAN CANDIDATE. THE PROOF RECORD AND EXTERNAL SUMMARY REMAIN
USER-WRITABLE, UNAUTHENTICATED, AND PROVENANCE-UNATTESTED; THE VERIFIER COULD
NOT READ THE EXTERNAL SUMMARY AND DID NOT INFER ITS COUNTS. THIS PACKET'S
IMPLEMENTATION AND VERIFICATION TASKS ARE COMPLETE, BUT ARCHIVE AND RELEASE
HAVE NOT BEEN PERFORMED OR AUTHORIZED. The implementation does not claim
fixed-root mutation containment. Remaining disclosed risks include stacked
unsynced deltas,
pre-mutation objective classification remains a judgment, oversized or
secret-bearing terminal output can require a new Owner-approved call, evidence
state is user-writable rather than attested, proof-root test behavior may differ
from a Git checkout, and default envelopes remain uncalibrated.

## Control-Plane Revision 2 Verification

- [x] The packet was reopened in place rather than creating another packet or
  active plan. `python scripts/sdd.py status` changed the packet from
  `44 complete, 0 pending` to `44 complete, 10 pending`; the incident-record
  task then advanced independently. The historical dogfood negotiation and
  recovery evidence was not deleted or presented as the active plan.
- [x] Added strict authority-manifest and compact technical-plan validation,
  including exact objective/task/repository identity, exact sorted
  paths/actions, exact optional push remote/branch, expiry, resource ceilings,
  schema closure, canonical digests, and authority-to-plan subset checks.
- [x] Added one out-of-tree objective workflow record with a single current
  plan digest, monotonically increasing revision, exact predecessor binding,
  bounded immutable plan bodies, and explicit superseded history. A second
  start with identical state recovers; a competing or stale start/revision
  refuses.
- [x] Added ordered phase admissions for plan peer, mutation, cross-review,
  proof, verification, integration, and optional push. Exact admission and
  evidence digests are required; a skipped, stale, duplicate, or mismatched
  phase refuses without advancing state.
- [x] Added an objective circuit independent of individual run IDs. Before
  worker start, two procedural failures, 900 controller-observed executor
  seconds, or USD 1.50 reported provider spend opens it. Reapproval alone is
  insufficient: resolution also requires changed plan, authority-scope, or
  mechanism identity. Authority timestamps and a new Owner-action digest do
  not masquerade as a material scope change.
- [x] Added stable blocker IDs and compact delta-review payloads containing only
  unresolved blockers and exact changed plan fields. The Claude prompt now
  scopes blocking review to technical correctness, security, contracts, and
  verification and explicitly denies the peer authority widening.
- [x] Added `workflow-start`, `workflow-revise`, `workflow-resolve`,
  `workflow-status`, `workflow-admit`, and `workflow-finish` to the existing
  controller CLI. CLI output is a bounded status summary; it omits the full
  authority and plan bodies.
- [x] Focused command:
  `python -m pytest adapters/codex/tests/test_orchestration_control.py adapters/codex/tests/test_orchestrator.py adapters/codex/tests/test_orchestration_evidence.py -q -p no:cacheprovider`
  with `PYTHONDONTWRITEBYTECODE=1` returned `94 passed in 45.30s`.
- [x] `python scripts/sdd.py verify orchestration-efficiency-hardening`
  returned exit zero and `Verified artifacts`; at that checkpoint it honestly
  reported `53 complete, 1 pending`.
- [x] `git diff --check` returned exit zero. Git emitted only expected
  worktree EOL-normalization warnings; it reported no whitespace error.
- [x] No Claude/provider call, mutating worker, dogfood retry, integration,
  commit, push, archive, release, publication, or deployment occurred during
  this tranche.
- [x] The first two local workflow bootstrap attempts failed before state or
  provider creation because this Codex PowerShell surface delivered empty stdin
  to the native child. The first attempt also used the unavailable
  `Convert.ToHexString` API; the second corrected digest computation but
  reproduced empty stdin. No third live bootstrap was attempted. The CLI now
  accepts `--payload-env <UPPERCASE_NAME>` as a bounded fallback, passes only
  the variable name in argv, removes the payload from its process environment
  immediately after reading, and refuses missing/empty/malformed names.
  Focused verification after that correction returned
  `95 passed in 44.92s`.
- [x] A follow-up source audit found two spec/implementation gaps before any
  provider call: the structured current plan was not bound to canonical packet
  `plan.md` bytes, and circuit defaults were not actually configurable. The
  controller now validates and rechecks the exact source-plan path/SHA-256
  before every executor admission and reads strict circuit thresholds from the
  authority manifest. A drift regression proves no admission is created and
  the phase remains unchanged. Focused verification returned
  `96 passed in 40.99s`.

## Current Result

THE SECOND OPUS 5 ARCHITECTURE ROUND CONVERGED AND THE CONVERGED
CONTROL-PLANE CORRECTIONS ARE NOW IMPLEMENTED LOCALLY. THE COMBINED FOCUSED
CONTROLLER, PEER-WRAPPER, EVIDENCE, AND PROCESS-RUNNER SUITE PASSED. THE
IMPLEMENTATION RECEIVED A CONVERGED BOUNDED OPUS 5 CROSS-REVIEW WITH NO
BLOCKERS. FROZEN FULL REQUIRED SUITES AND SEPARATE VERIFICATION HAVE NOT YET
RUN, SO THE PACKET REMAINS OPEN AND IS NOT ARCHIVED, RELEASED, INSTALLED, OR
READY FOR DOGFOOD.

## Control-Plane Architecture Peer Evidence

- [x] Round one used the same durable objective workflow and run:
  objective `05899a284437257a2e5bf84cc1e7ababd5428ffd6be94088a9362541bbd31273`,
  run `b2382adf30e14e9f89a72038666937a5`, structured plan revision one
  `dc02996f5428724f2fa1764d979774fc0af42e02bf9a6f7dfadd5b3076b12976`.
  Opus 5 returned five technical blockers. The call used 20,863 outbound bytes,
  237.228 provider seconds, and USD 0.6694075. It was recorded as
  `technical_blocker`, not a procedural failure.
- [x] The canonical `plan.md` and delta spec were revised without opening a new
  packet, objective, or run. Structured plan revision two exactly superseded
  revision one as
  `1e751374f31a0e4155649db1bd1976e210fa85c995df69a3be8a07384322d128`
  and bound canonical plan SHA-256
  `802a688395ec53057201f63c82d26d439b1a991a12e435a8eadf494ea7ffafce`.
- [x] The compact final delta was 9,126 bytes with SHA-256
  `e5a11c01294c625081194a1568f94c81f3252ea5bc9116640f7308f9acd0c472`.
  Opus 5 returned `converged: true` with no blocking concerns. The call used
  10,079 outbound bytes, 135.934 provider seconds, and USD 0.3982485.
- [x] Cumulative plan-peer evidence remained inside the original objective
  circuit: 30,942 outbound bytes, USD 1.067656 observed provider spend, zero
  procedural failures, and a closed circuit. The workflow finished `complete`
  at plan revision two. The persisted result body SHA-256 is
  `e01d6e3781d75658b028a705c37146776b2d2630d43cc2638f67f8c4317b4ec5`.
- [x] Implemented immutable Owner-issued objective IDs, the one-time
  Owner-action ledger, objective-wide post-worker circuit, explicit
  retry/invalidation graph, crash-burn recovery, immutable plan-body checks,
  bounded payload files, review-input identity, `insufficient_context`, and
  fail-closed feature/push paths.
- [x] Wired single-use admission consumption into the official peer, mutation,
  cross-review, proof, verifier, and integration paths. Official mutation now
  rechecks and commits one clean isolated candidate after the worker is
  quiescent. Integration separately rechecks the clean unchanged Owner base and
  exact candidate, consumes its admission, performs only a fast-forward, and
  verifies the integrated v2 identity. Push remains unavailable.
- [x] Actual Windows regressions exercised cross-process single-winner
  Owner-action consumption, concurrent atomic JSON replacement without torn
  reads, linked-worktree configuration, and junction/reparse refusal. The
  payload-file symlink case remained skipped because this Windows account
  cannot create a symlink; that skip is not reported as positive symlink
  evidence.
- [x] Focused command:
  `python -m pytest adapters/codex/tests/test_orchestration_control.py adapters/codex/tests/test_orchestrator.py adapters/codex/tests/test_orchestration_evidence.py adapters/codex/tests/test_process_runner.py -q -p no:cacheprovider`
  with `PYTHONDONTWRITEBYTECODE=1` returned
  `179 passed, 1 skipped in 128.53s`.
- [x] The first bounded implementation cross-review attempt used durable run
  `124c677c0b484046994f81da00b48718`, one 263,313-byte Opus 5 request,
  420.065 provider seconds, and USD 2.1257315 reported provider cost. It
  terminated as `error_max_budget_usd` / `structured_budget_ceiling` and
  produced no critique. The run was closed `blocked`; absence of a verdict was
  not treated as convergence, and no second call was started automatically.
- [x] The Owner authorized one fresh two-part bounded review under durable run
  `34a37ee3aaa14dde9e60eb1a67559cac`. Part one sent a 62,245-byte
  controller/peer-boundary packet to Opus 5 and timed out after 450.073
  provider seconds with bounded Windows Job cleanup; provider cost remained
  unknown and no verdict was emitted. Part two sent a 64,338-byte combined
  high-risk controller/executor packet to the CLI-confirmed
  `claude-fable-5` model. It ran 217.935 provider seconds, reported
  USD 1.679656 and 16,255 Fable output tokens, then returned
  `error_max_budget_usd` under the USD 1.50 call ceiling. No critique was
  emitted. The two-call cap was exhausted, the run was closed `blocked`, and
  no third call was started. These observations show that input partitioning
  alone does not bound high-effort reasoning/output cost.
- [x] Corrected that observed failure mechanism before another provider call.
  Peer invocations now accept only explicit review kinds
  (`plan`/`implementation`) and CLI effort values
  (`low`/`medium`/`high`/`xhigh`/`max`). Official workflow phases bind
  `plan_peer` to plan review and `cross_review` to implementation review.
  Review kind, requested effort, and selected resource-ledger phase enter the
  durable invocation identity and result evidence.
- [x] Added hard accepted-output bounds for the overall assessment, every
  blocker/gap/risk/context item, task text and rationale, and all arrays.
  Implementation review requests an empty decomposition when no blocker exists
  and only minimal remediation tasks otherwise. This does not claim to measure
  or cap hidden provider reasoning, account usage, or every provider-side cost.
- [x] Focused peer-adapter verification with bytecode and pytest cache writes
  disabled returned `55 passed in 17.85s`. It proves explicit medium-effort
  argv routing, review-kind prompts and ledger phases, durable fingerprint
  separation for both controls, pre-spawn refusal of unsupported controls, and
  runtime enforcement of structured-output bounds. Its maximum-shape
  regression proves only that the ASCII critique JSON stays below half of the
  64 KiB durable terminal-record ceiling. It does not prove worst-case
  multibyte UTF-8 or the complete stored result body; no positive headroom
  claim is made for those cases.
- [x] The combined focused control-plane, peer-wrapper, evidence, and
  process-runner suite then returned
  `188 passed, 1 skipped in 137.66s`. The skip remains the unavailable Windows
  symlink privilege case; the real junction/reparse regression passed and no
  positive symlink result is inferred.
- [x] One fresh bounded implementation cross-review used durable run
  `4023d50c6a624175afd1baf541d87bab` against clean commit
  `5f3f5704cd8995697a027e4e5583969fab48a383` and executable fingerprint
  `55d7812b3b71f843c9170994a6e2eb2a82afe70d62ffd06783a1b832db0324f4`.
  The exact review body was 42,417 bytes; the complete outbound prompt was
  44,311 bytes. The controller requested `claude-opus-5`,
  `review_kind=implementation`, `effort=medium`, one call, USD 1.25, and 480
  seconds. It returned after 79.835 provider seconds with observed cost
  USD 0.4105505, a persisted terminal body, `context_status=sufficient`,
  the exact review-input digest, `converged=true`, and zero blocking concerns.
  No retry or second peer call ran.
- [x] The peer recorded five non-blocking gaps and four risks in
  `claude-architecture-review-round-15.json`. The ASCII-only headroom
  overclaim above was narrowed immediately. The unchanged CLI parser was
  checked locally: `--workflow-phase` accepts only `plan_peer` or
  `cross_review`, so the peer's conditional `KeyError` concern is not reachable
  through this CLI surface. No absence of coverage for the remaining gaps is
  treated as a positive result.
- [ ] Freeze the unchanged executable fingerprint, run the full required
  suites, and obtain separate verification before any mutation dogfood,
  integration, push, archive, release, or installation claim.
