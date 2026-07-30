# Verification

## Change

codex-host-mvp

## Automated Checks

- [x] Disposable verifier hook script compiled under Python 3.11.
- [x] Disposable hook JSON and personal/project agent TOML parsed successfully.
- [x] Test repository was fixed at commit
  `167a1415c36cba2d52a78098a63748e910837bc1`.
- [x] `python scripts/sdd.py verify codex-host-mvp` — exit 0; artifacts valid,
  16 tasks complete and 11 pending. The pending tasks remain visible and archive
  would require force.
- [x] `python scripts/check_sync.py` — all 11 root/scaffold pairs identical.
- [x] `python -m pytest -q` — 501 passed, 6 skipped in 73.03 seconds.
- [x] Delta grammar inspection — 3 attributed capabilities, 20 canonical
  requirements, zero heading issues.
- [x] `git diff --check` — exit 0 for tracked changes; an explicit trailing
  whitespace scan over the new untracked blueprint/packet files returned no
  matches.

## Manual Checks

- [x] Claude Code 2.1.173 discovered outside PATH at
  `C:\Users\Daniel Paez\.local\bin\claude.exe`.
- [x] `claude auth status --json` returned exit 1, `loggedIn: false`,
  `authMethod: none`.
- [x] One bounded headless Claude call returned exit 1, parseable JSON,
  `is_error: true`, misleading `subtype: success`, `Not logged in`, and zero
  cost in 3.61 seconds.
- [x] After Owner login, `claude auth status --json` returned exit 0 with
  `loggedIn: true`, first-party authentication, and a Claude Max subscription.
- [ ] Authenticated Fable round trip — the single attempt used tools disabled,
  plan-only permissions, no session persistence, one turn, a $0.10 ceiling,
  schema-locked output, and a 60-second wrapper. It produced no result before
  the wrapper timed out, so no success envelope, schema result, usage, or cost
  was observed.
- [x] Timeout cleanup — the wrapper left CLI PID 19756 running. Its executable
  path and start time identified it as the just-started local Claude CLI;
  exact-PID termination succeeded, while the pre-existing Claude desktop
  processes were left untouched.
- [x] Exact Opus 5 access — the Owner approved Opus 5 as the Fable fallback.
  One call used fixed model ID `claude-opus-5`, low effort, tools disabled,
  plan-only permissions, no persistence, no model fallback, a $1 ceiling, and
  a process-level 120-second timeout. It reached `claude-opus-5` and exited in
  6.9 seconds with no lingering CLI process.
- [ ] Opus 5 schema result — the CLI returned exit 1,
  `subtype: error_max_turns`, `is_error: true`, `stop_reason: tool_use`, and
  `terminal_reason: max_turns`. The JSON-schema mechanism requires an internal
  structured-output tool round, so `--max-turns 1` prevented the result. No
  file/shell tool or server web-search/web-fetch activity was reported.
- [x] Opus 5 usage evidence — CLI-reported usage was 2,273 input tokens, 49,713
  one-hour cache-creation tokens, 88 output tokens, and $0.510695 equivalent
  cost.
- [x] Corrected Opus 5 request pre-spawn guard — 23 explicitly scoped
  repository files produced a 202,820-byte review bundle; the existing
  `content_has_secret` scanner returned false before the CLI was launched.
- [ ] Corrected Opus 5 schema result — the call used the fixed
  `claude-opus-5` ID, high effort, tools disabled, plan-only permissions, safe
  mode, no persistence, no model fallback, `--max-turns 2`, a $1 ceiling, and
  a 180-second process deadline. The wrapper reached its deadline with no
  stdout or stderr, killed the exact CLI process, and found no lingering
  process. No response, schema result, model-usage envelope, or cost was
  observed; the outcome is incomplete, not a pass or architectural verdict.
- [x] Minimal Opus 5 transport/schema probe — a separate call isolated the
  adapter contract from architecture review and used the exact
  `claude-opus-5` model, low effort, tools disabled, plan-only permissions,
  safe mode, no persistence, no fallback, `--max-turns 2`, a $0.10 ceiling,
  and a 60-second process deadline. It returned exit 0, `is_error: false`,
  `num_turns: 2`, `terminal_reason: completed`, and the complete required
  structured envelope in 7.6 seconds. Server web search/fetch counts and
  permission denials were empty, no process lingered, and total reported cost
  was $0.0597185. The requested empty blocker list proves schema transport
  only and is not counted as architecture convergence.
- [x] A custom verifier with `fork_turns: none` received no exact parent-only
  canary, read the expected committed input, and used model `gpt-5.6-terra`.
- [x] Under a read-only parent, the custom verifier's write attempt was denied
  and no sentinel appeared.
- [x] Under a `danger-full-access` parent, the same custom read-only verifier
  inherited `danger-full-access` and successfully wrote the sentinel.
- [x] A separate ephemeral `gpt-5.6-terra` process launched with `-s read-only`
  read the expected input and commit, received exit 1/access denied on the
  exact write attempt, and left no sentinel.
- [x] A project-scoped `.codex/agents/` verifier was discovered and ran as
  `gpt-5.6-luna` with read-only sandbox against the expected commit.
- [x] Prior hook spike: plugin trust, Bash/apply_patch/MCP/local-function and
  nested coverage, user disable, fresh-task boundary, Windows commands, and
  definition-vs-handler upgrade behavior were exercised on this machine.
- [x] First Codex-family blueprint review returned BLOCKED: ambiguous
  modify+rename of the legacy fail-open requirement, contradictory legacy
  Purpose, non-canonical handler revision, and a non-blocking “unavailable”
  branch for running handlers.
- [x] Enforcement delta replaced with an additive
  `codex-plugin-enforcement` capability requiring a canonical executable
  bundle digest, definition-trusted runtime verification, explicit deny for
  running-handler failures, and readiness invalidation for command-start
  failures.
- [x] Second Codex-family review returned BLOCKED: the mutable bootstrap could
  not authenticate itself, and the new peer contract omitted empty-plan
  refusal plus the unclosable data boundary.
- [x] Integrity design corrected so the verifier program and digest live
  literally in the trusted hook command and execute before mutable plugin
  files; peer delta now preserves empty/secret pre-spawn refusal, fence
  escalation, and the structured critique/decomposition contract.
- [x] Third Codex-family review — separate ephemeral `gpt-5.6-terra`,
  read-only, strict schema — returned `PASS WITH OPEN QUESTIONS`, no findings.
  The repository fingerprint was identical before and after:
  `f697be008a4c8dce9d08b4a7024362077b00b7f1ab01a76c8752ba43effd7c8e`.
  This proved process isolation but not a different epistemic vantage.
- [x] Owner-relayed Claude architectural review returned `converged: false`
  with three blockers: missing execution worktree containment, a
  verify-then-import TOCTOU race, and unsafe reuse of Claude-specific hook
  dispatchers.
- [x] Worktree omission confirmed: neither the blueprint nor its deltas carried
  the six containment guarantees already specified by `codex-conductor`.
- [x] Dispatcher defect reproduced:
  `protect_secrets.check("apply_patch", {"file_path": ".env"})` and
  `check("new_tool", ...)` returned allow, while `check("Write", ...)` and
  `check(None, ...)` denied.
- [x] Stateful-hook claim confirmed: packet, orientation, and completion hooks
  depend on `_drydock_common` state/discovery and are not pure policy
  functions.
- [x] Negotiation baseline confirmed: `negotiate.py` refuses empty/secret plan
  input, uses a content fence, caps rounds, returns structured decomposition,
  and distrusts `converged: true` when blockers remain.
- [x] Initial correction added one-writer worktree requirements, no-auto-merge
  and truthful gates, verify-once/execute-same-bytes integrity, pinned imports,
  fail-closed matched mappings, pace-first routing, and separate
  isolation-versus-epistemic claims.
- [x] Owner-relayed second Claude review returned `converged: false`: the first
  three blockers were closed, but nested execution could not enforce worktree
  containment because live parent permissions can widen its sandbox.
- [x] Separate mutation-process live probe from a `danger-full-access` parent —
  Codex CLI
  `0.146.0-alpha.3.1`, `gpt-5.6-terra`, `--ephemeral`,
  `-s workspace-write`, and `-C` fixed to a disposable Git worktree — created
  `inside.txt` in the assigned root and rejected an attempted sibling
  Owner-checkout write as outside the project.
- [x] Independent probe verification — Owner HEAD remained
  `a32e16a9ca2bd89bf08640ee77c09ef39a02754c`; Owner status remained clean;
  README SHA-256 remained
  `C11955B240240EA9AE919CC5E148044069EA4CC1CF0C28638B0179438B2CEDA8`;
  `outside.txt` was absent; worker status contained only `?? inside.txt`; and no
  Codex core process lingered.
- [x] Probe economics — 67,118 input tokens (48,896 cached), 461 output tokens,
  and 27.1 seconds for the two-write containment probe.
- [x] Probe cleanup — direct recursive deletion was denied before execution by
  the active safety policy. The already-verified disposable probe directory was
  then moved to the Windows Recycle Bin; no product or Owner file was removed.
- [x] Latest blueprint/deltas now use a separate fixed-root mutation process,
  atomic exclusive worktree lease, Owner-state fingerprinting, narrow guarded
  matchers, CI bundle-sync, and a normalized reproducible plain-source bundle.
- [x] Owner-relayed final Claude re-review returned `converged: true` with no
  blocking concerns. Its overall verdict explicitly found the architecture
  sufficient to begin once Phase 0 passed. The local exact-Opus-5 transport
  probe had already passed; the review's stale statement that authenticated
  transport remained unproven was not adopted.
- [x] Final peer gaps reconciled — the mutation contract now requires
  timeout-plus-grace stale-lease reclamation only after exact dead-process
  proof, runner-owned Git metadata mutations, bounded orphaned-lease cleanup,
  and explicit evidence that workspace-write confinement held under a
  `danger-full-access` parent.
- [x] Plugin layout spike — the current plugin validator rejected both a
  manifest `hooks` override and a custom non-root `skills` path. The current
  Codex manual also confirms default plugin hook discovery at
  `hooks/hooks.json`. The implementation therefore uses a self-contained
  `adapters/codex/drydock/` plugin root and a deterministic packaged scaffold
  bundle rather than exposing the existing Claude hooks to Codex.

## Phase 1 Implementation Evidence

- [x] Owner approval — the Owner explicitly said “ok lets go” after Claude
  returned `converged: true` with no blocking concerns.
- [x] Plugin layout — `adapters/codex/drydock/` is self-contained. Its
  manifest keeps `skills: "./skills/"`, omits the validator-rejected `hooks`
  override, and passes the installed Codex plugin validator.
- [x] Scaffold provenance — the deterministic UTF-8 JSON bundle contains 38
  digest-verified files from `assets/project-scaffold/`. It deliberately
  excludes `CLAUDE.md` and the legacy fail-open, Claude-install-dependent
  `.codex` hook bridge. Exact source-to-bundle rebuild comparison passes.
- [x] Initialization — preview performs no writes; apply uses
  create-exclusive writes, preserves conflicting Owner files, merges only
  missing `.gitignore` lines, refuses detected symlink parents, and never
  installs `.git/hooks`.
- [x] Readiness — plugin, Python, bundle, repository, and project-context
  evidence are reported separately. Enforcement remains false with trust
  unknown and task liveness unavailable; peer status is `not_checked`.
- [x] Targeted tests —
  `python -m pytest adapters/codex/tests -q -p no:cacheprovider` returned
  `14 passed, 2 skipped`. Both skips are Windows symbolic-link creation tests
  because this account lacks the required symlink privilege; they are not
  claimed as positive evidence.
- [x] Compatibility suite —
  `python -m pytest tests -q -p no:cacheprovider` returned
  `501 passed, 6 skipped`.
- [x] Scaffold compatibility — `python scripts/check_sync.py` returned
  `OK: all 11 root/scaffold pairs are identical.`
- [x] Current-machine Codex CLI discovery found the packaged WindowsApps
  executable, but invoking `--version` returned Windows access denied.
  Readiness records this as `unavailable`; it does not infer the app version
  from the running desktop task.

## Phase 2 Implementation Evidence

- [x] Narrow matchers — the generated definition matches only canonical
  `Bash` and `apply_patch`. MCP tools, other local functions, hosted tools, and
  specialized opted-out paths remain explicitly uncovered. A contract
  mismatch inside the runtime denies rather than guessing.
- [x] Definition-bound integrity — every hook command embeds a complete
  base64-encoded minimal verifier and the canonical runtime SHA-256. It starts
  Python with `-I -S`, accepts only one manifested Python file in the hook
  directory, reads it once, verifies the captured bytes, pins `sys.path` to
  standard-library roots, and compiles/executes those same bytes in memory.
- [x] Reproducibility — runtime, manifest, and definition are deterministic
  plain UTF-8/LF files. Exact rebuild checks run in the existing Windows/Linux
  CI matrix and in release preflight. The Codex manifest is now a fifth
  version location in release drift checks.
- [x] Adversarial adapter suite — the combined targeted run returned
  `37 passed, 2 skipped`. It proves secret/destructive-Git/high-risk packet
  denial, malformed-contract denial, runtime tamper denial, unmanifested
  Python denial, startup-injection resistance, Windows path/command execution,
  session-revision liveness, and the Codex-native Stop gate.
- [x] File-swap regression — a verified test runtime replaced its own on-disk
  file after capture. The current invocation emitted only
  `CAPTURED_EXECUTED`; the replacement never executed. The next invocation
  returned the structured integrity deny.
- [x] Exact Windows hook command — the generated `commandWindows` is 2,761
  characters, below the exercised 8,191-character boundary, and ran
  successfully from the real plugin path containing `Daniel Paez`.
- [x] Readiness remains honest — definition validity and the handler revision
  are reported, but enabled/trusted/managed remain `unknown` and enforcement
  remains inactive until a fresh Codex task supplies current-revision
  liveness plus host trust evidence.
- [x] Installed plugin validator passes with the generated nested
  `hooks/hooks.json`; no validator-rejected manifest hook override is used.

## Phase 3 Orchestration and Boundary Evidence

- [x] Focused process-runner/orchestrator regression run returned
  `61 passed` in 68.16 seconds.
- [x] Post-hardening runner regression returned `47 passed` in 68.23 seconds.
- [x] Complete Codex adapter suite was refreshed after the release-gate edits
  and returned `94 passed, 2 skipped` in 95.41 seconds. The two Windows
  symbolic-link privilege skips are not counted
  as positive evidence.
- [x] Complete legacy/Claude-host compatibility suite was refreshed after the
  release-gate edits and returned `548 passed, 6 skipped` in 79.66 seconds.
- [x] Git-control poisoning regression — the fake worker appended
  repository-local `core.fsmonitor` and `core.hooksPath` values pointing at an
  executable sentinel. The direct control fingerprint changed, mutation
  refused before any post-worker Git command, and the sentinel was absent.
- [x] Git-control hardening — worktree Git and Owner fingerprint commands pin
  filesystem monitoring, hooks, external attributes, external diff, symlink,
  and untracked-cache behavior. The bounded direct-byte fingerprint covers
  repository/worktree config, active HEAD/refs, indices, hooks,
  attributes/excludes, alternates/replacements, and worktree admin pointers.
- [x] Executable/config hardening — the runner resolves Git only from absolute
  PATH entries and all Git subprocess arguments begin with that absolute file.
  Parameterized regressions prove local config include directives and external
  clean filters refuse before worktree creation or worker spawn.
- [x] Final boundary audit — the reserved-container ignore preflight now uses
  the same absolute Git discovery and pinned local configuration as every
  later runner call. A regression lowers the 100,000-entry worktree scan
  limit, fails if iteration requests an item beyond that bound, and proves
  both extraction and recursive cleanup refuse rather than materialize or
  traverse an unbounded worker-controlled tree.
- [x] Owner drift is checked after worker quiescence and before extraction.
  The hostile Owner-drift regression returned no changed files or diff and
  reported applicability `not_evaluated`.
- [x] Windows process identity is captured while the child is suspended inside
  its kill-on-close Job Object. Machine output now reports only
  `windows_job_descendant_lifetime_contained`; it does not label that mechanism
  filesystem confinement.
- [x] Live current-runner mutation — exact model `gpt-5.6-terra` created only
  `drydock-live-probe-2.txt` with byte-exact
  `absolute-git-ok\n` in reserved worktree `ceb8a49d5d38`. The worker
  exited zero in 27 seconds; Owner HEAD and fingerprint were identical;
  Git-control SHA-256 remained
  `be82e3e0f21d3ecdc679611846afbd8cdd08fcb67c34085083a94f175a20b165`;
  ignored files were empty; lease released; `merged` was false; and the
  mutation-only stage was `review_required`, not green.
- [x] Exact live cleanup removed only worktree
  `.drydock-worktrees/ceb8a49d5d38` and its reserved branch. A subsequent
  `git worktree list --porcelain` listed only the Owner `main` worktree.
- [x] Live current-runner mutation after final boundary hardening — exact
  model `gpt-5.6-terra` created only `drydock-live-probe-3.txt` in reserved
  worktree `26b09a62a33f`. Direct byte inspection returned 21 bytes with hex
  `626F756E6465642D707265666C696768742D6F6B0A`, exactly
  `bounded-preflight-ok\n`. The child exited zero in 19.5 seconds; Owner and
  Git-control fingerprints were identical; ignored files were empty; the
  lease released; `merged` was false; and the result remained non-green
  `review_required`. Exact discard then removed only that reserved worktree
  and branch, and `git worktree list --porcelain` again listed only Owner
  `main`.
- [x] Live current-runner verifier — a separate ephemeral read-only
  `gpt-5.6-terra` process completed two requested Git observations in
  24.3 seconds and returned schema-valid `PASS`. Exact HEAD
  `5f76f67eda90d92b4f0eea1908e66c7f45ca81f7` and working-tree fingerprint
  `4be00377acd5832a2cab473c09c210945955dc33c86e5c92bafbba9352415060`
  were identical before and after. This proves the requested current-state
  observations and write/lifetime boundary, not epistemic diversity.
- [x] Deterministic parity checks passed: all 11 root/scaffold pairs,
  project-scaffold bundle, hook runtime/definition, and five version locations
  at `0.12.1`.
- [x] Final Opus convergence — the first exact-Opus-5 high-effort review
  refused before spawn because the outbound secret scanner matched a synthetic
  fixture. After exact fixture redaction, the full bundle exited
  `error_max_budget_usd` at the $1.25 ceiling without a critique. A focused
  retry and a still-smaller blocker-only retry each reached their 300-second
  timeout without a critique. Every returned peer status still reported
  first-party authentication ready and requested model `claude-opus-5`; none
  reported Fable quota exhaustion or model unavailability. These outcomes are
  not agreement, rejection, or evidence about the code. The later
  Owner-relayed, read-only two-repository Opus review completed and returned
  `converged: true` with no blocking concerns. It independently reproduced
  legacy `548 passed, 6 skipped`, Codex adapter `94 passed, 2 skipped`, sync
  `11/11`, all bundle/version checks, packet `33 complete, 2 pending`, and
  LaunchGuardian `81 passed`; inspected the decoded hook bootstrap, hostile
  runner boundaries, verifier disclosures, peer failure semantics,
  disposition code, retained raw/normalized findings, and all 16 pinned
  Action refs; and found no reachable fail-open or unsupported green state.
  Its five gaps, six risks, and four non-blocking changes remain preserved in
  `claude-final-review-result.md`. The review explicitly does not establish
  epistemic diversity, in-situ hook enforcement, Action SHA provenance, or
  release readiness.
- [x] LaunchGuardian source-build gate — companion commit
  `24abba5c9cd3eb723356e7ec0de640b7c8278680` produced the UTF-8 strict
  framework scan at `2026-07-25T15:16:29.577002Z` with all five scanners
  `ran`, LGF validation valid, and report schema `0.2.0`. It returned
  `APPROVED_WITH_DISPOSITIONS`, not plain `APPROVED`: raw Semgrep contains
  exactly 6 results from the two Owner-approved Python-3.6 compatibility rule
  IDs and 0 errors. All six remain visible as High with original
  `blocks_launch: true`; exact status `not_applicable` leaves 0 open blocking
  findings. No wildcard, path exclusion, inline ignore, deletion, severity
  downgrade, or Critical override is used. The companion commit returns 80
  tests passed, builds wheel and sdist successfully, and completes its own
  strict five-scanner scan. Installed/PyPI LaunchGuardian 0.2.0 does not yet
  implement this report behavior, and approver metadata is not authenticated
  identity proof.
- [x] LaunchGuardian companion release hardening — descendant commit
  `c754062dc1c35dce06cfc6f7946909287f1ce1fc` pins all 16 repository and
  distributed-template GitHub Action references to verified 40-character
  commits and adds a regression that rejects mutable refs. Its suite returns
  81 passed. After generated package-build residue was moved outside the
  source checkout, the strict self-scan at `2026-07-25T15:27:56.088651Z`
  ran all five scanners and returned point-in-time `APPROVED`, 0 normalized
  findings, and 0 raw Semgrep errors. The earlier scan of the generated copy
  produced findings and was not reported as a pass or hidden with an
  exclusion.
- [x] Historical Desktop readiness dogfood for handler
  `86a863559de9b76eb49cb8a6206553ea4569cf03b3ddb10f40719bb687485ffe`
  — after CLI review/trust, a new Desktop
  task executed SessionStart and wrote a liveness record for task
  `019fa333-1ff4-76d0-901d-2d392973f80b`, repository
  `C:\Users\Daniel Paez\drydock`, model `gpt-5.6-sol`, and runtime digest
  `86a863559de9b76eb49cb8a6206553ea4569cf03b3ddb10f40719bb687485ffe`.
  The skill's documented no-argument readiness invocation nevertheless
  returned `active_task_liveness: unavailable`. Supplying that exact task ID
  and plugin-data root manually returned `current_revision_observed`. This
  proves trusted SessionStart execution and exposes a readiness-adapter
  blocker; it is not a completed dogfood pass. The corrected source invocation
  then resolved that same record with no manual flags and reported
  `session_id_source: CODEX_THREAD_ID`,
  `plugin_data_source: codex_home_plugin_data`, exact repository root, and
  `current_revision_observed`. Regression coverage proves unique discovery,
  explicit-argument precedence, repository-mismatch rejection, and ambiguous
  root refusal. Codex adapter tests return 98 passed, 2 skipped; legacy tests
  return 548 passed, 6 skipped; sync 11/11, scaffold bundle, unchanged hook
  bundle, version parity, and compilation all pass. The refreshed installed
  cache contains the same 15 files with 0 byte differences. Rerunning the
  ordinary readiness skill in that same fresh task returned
  `current_revision_observed`, exact repository/runtime/task evidence,
  `session_id_source: CODEX_THREAD_ID`, and
  `plugin_data_source: codex_home_plugin_data` with both resolution errors
  null. It correctly retained `active: false`, `trusted: unknown`, and
  `ready_for_enforcement: false`; PreToolUse interception is recorded
  separately below rather than inferred from SessionStart.
- [x] Historical Desktop PreToolUse dogfood for handler
  `86a863559de9b76eb49cb8a6206553ea4569cf03b3ddb10f40719bb687485ffe`
  — in that same current-revision task,
  canonical `Bash` denied the exact inert command
  `Set-Content -WhatIf -LiteralPath
  '.env.drydock-live-probe-7f1c9e42' -Value 'probe'`, and canonical
  `apply_patch` denied an Update File patch targeting the same guaranteed-
  absent path. Both returned the exact Drydock secrets-guardrail reason. A
  final `Test-Path` returned exit 0 and `False`. The shell probe could not
  write because of `-WhatIf`; the patch probe could not create the absent file
  because it used Update File. This is point-in-time interception evidence for
  the two defined contracts on the tested build, not evidence for uncovered
  MCP, other local, hosted, or specialized paths and not a managed or Tier 4
  claim.
- [x] Scoped post-convergence Opus review — the exact requested
  `claude-opus-5` reviewed `07d2be3..40adbf5` through the bounded controller
  and returned `converged: false` with one blocker after 201.3 seconds. The
  thread-keyed record carried no time, nonce, or per-invocation marker, so a
  stale resume could return `current_revision_observed`. Repository inspection
  reproduced the defect: the record had no freshness field and the positive
  regression hand-wrote its evidence. The first output wrapper lost its pipe
  and was not counted as a verdict. The clean retry cost `$0.6880055` against
  a `$1.25` ceiling. Exact scope and residual gaps are recorded in
  `claude-readiness-review-result.md`.
- [x] Scoped Opus correction review — exact `claude-opus-5` reviewed
  `40adbf5..79cb83f` in 218.5 seconds and returned `converged: true` with no
  blocker. It found the explicit probe, recent activity record, bounded system
  clock, linked-path rejection, and unsigned/in-window replay disclosures
  sufficient to proceed to exact-digest install/live dogfood under the
  cooperative non-managed profile. It explicitly did not authorize release,
  archive, merge, or publication. Cost was `$0.8256345` against a `$1.25`
  ceiling. The final independent review remains pending until it can inspect
  the live evidence for the installed digest.
- [x] Hook-probe freshness correction — only a supported Bash command
  tokenizing to `drydock_codex.py`, immediately followed by `readiness`, and
  containing exact token `--hook-liveness-probe` writes a separate atomic
  activity record; the readiness process also confirms the probe flag was
  requested. The marker writes only after deterministic policy allows the
  command. SessionStart's packet baseline remains unchanged. Readiness requires
  the same task, runtime digest, resolved repository,
  event/tool/probe kind, a 10-second maximum system-clock age, and a 2-second
  future-skew bound. It rejects missing, expired, materially future,
  repository-mismatched, linked/junctioned, or ambiguous evidence and reports
  the record as unsigned/user-writable cooperative evidence. An attempted
  cross-process monotonic design failed on this machine because hook Python
  3.14 and readiness Python 3.11 differed by about 43.7 seconds while their
  wall clocks differed by about 67 milliseconds; the failed test was retained
  until the mechanism changed. An unsigned marker may still replay inside the
  disclosed 10-second window. Current model and permission-mode fields come
  from that fresh activity record, not the unbounded SessionStart record.
- [x] Freshness correction verification — focused hook/readiness tests return
  `37 passed, 1 skipped`; the full Codex adapter returns `109 passed, 2
  skipped`; the full legacy/Claude-host suite remains `548 passed, 6 skipped`.
  The two Codex skips are the pre-existing Windows symlink-privilege tests;
  all three new Windows junction regressions ran. Generic Bash, quoted false
  probes, apply_patch, and a policy-denied readiness-shaped command do not
  write an acceptable activity record; exact time boundaries pass. The
  generated-definition test decodes the inline verifier and proves its
  `EXPECTED` value and injected
  `DRYDOCK_RUNTIME_SHA256` both bind the runtime manifest digest. Sync remains
  11/11, scaffold and
  generated-hook rebuild comparisons pass, compilation passes, and
  `python scripts/release.py --check` reports all five version locations at
  `0.12.1`. The corrected handler revision is
  `a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`.
- [x] Exact-handler install and fresh-task liveness dogfood — the installed
  cache matched all 22 source files at commit
  `d4d63111b4d82735cd135cb8439a3c97bd26d568`. After the stale Desktop
  backend was fully terminated and restarted, task
  `019fa3ba-1935-7e73-87da-6587d087ea2a` returned
  `current_revision_observed` for handler
  `a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`.
  Its 363-millisecond-old `PreToolUse`/`Bash` activity record supplied the
  current `gpt-5.6-sol` model and `bypassPermissions` context and matched the
  exact repository root and runtime digest. The report retained every stated
  limitation: unsigned user-writable plugin data, a 10-second replay window,
  wall-clock dependence, `active: false`, `trusted: unknown`, empty covered
  paths, and `ready_for_enforcement: false`.
- [x] Exact-handler selective deny dogfood — canonical `Bash` denied
  `Set-Content -WhatIf` against `.env.drydock-a04c-live-probe`, and canonical
  `apply_patch` denied an Update File patch against the same guaranteed-absent
  path. Both returned the exact Drydock secrets-guardrail reason. A final
  `Test-Path` returned exit 0 and `False`. These are point-in-time observations
  of the two defined contracts, not evidence for MCP, hosted, specialized,
  renamed, or other local tool paths. One later large, multi-file
  `apply_patch` invocation failed closed with the bootstrap's generic runtime
  integrity message. Direct SHA-256 measurements immediately afterward showed
  both installed and source `runtime.py` at the expected `a04cf380...` digest,
  their text compared equal, and smaller guarded `apply_patch` calls succeeded.
  The failed invocation made no changes. Its cause was unresolved at this
  point; the final peer review below later reproduced a locale-decoding cause
  without relabeling the denial as detected tamper.
- [x] Final exact-handler peer review — two authenticated bounded
  `claude-opus-5` CLI attempts returned no verdict. The first duplicated full
  current sources after the exact delta and exhausted its configured `$1.25`
  ceiling after 222.2 seconds. One right-sized retry removed the duplicated
  sources and exhausted the same ceiling after 283 seconds. Both returned
  `process_failure` / `error_max_budget_usd`, without a schema-valid envelope,
  model-usage proof, critique, or cost evidence. Neither is counted as a
  review. The bounded manual-chat relay is saved in
  `claude-final-readiness-review-request.md`. The Owner-relayed repository-aware
  Claude review then returned `converged: true` with no blocking concerns,
  reproduced the Git identities, `37 passed, 1 skipped` focused,
  `109 passed, 2 skipped` adapter, sync 11/11, packet 38/2, and all eight
  decoded digest chains. It identified the earlier generic integrity denial as
  a host-locale stdin decoding failure under `-I -S`, plus four other
  non-blocking precision/portability findings. The complete bounded result and
  five required follow-ups are saved in
  `claude-final-readiness-review-result.md`. Because the manual relay has no
  successful controller envelope, exact model observation is not claimed from
  controller evidence.
- [x] Final packet consistency refresh — `python scripts/sdd.py verify
  codex-host-mvp` reports `39 complete, 1 pending`; one integrated end-to-end
  workflow run remains explicit.
- [ ] Integrated workflow negotiation — exact Opus 5 returned schema-valid,
  model-observed critiques in both configured rounds but did not converge.
  Round 1 cost `$0.2588095`; Round 2 cost `$0.4821165`. No mutation process or
  worktree started. Codex's post-cap audit found that the runner already
  rejects `.git` pointer drift before explicit-root Git extraction and that an
  identical `-X utf8=1` discriminator clears the locale-cause uncertainty.
  The peer has not reviewed those rebuttals, so agreement is not inferred.
  Full evidence is in `integrated-dogfood-negotiation.md`.

## Documentation Updates

- [x] `docs/CODEX_HOST_BUILD_BLUEPRINT.md` added.
- [x] Change packet brief, plan, tasks, decisions, and verification populated.
- [x] Delta specs added for Codex host behavior, orchestration, and enforcement.
- [x] Cross-model blocking review reconciled into the blueprint and packet.
- [x] A bounded re-review prompt is saved as `claude-rereview-request.md`.
- [x] The scoped readiness re-review result is saved as
  `claude-readiness-review-result.md`.
- [x] The final exact-handler review request and converged result are saved as
  `claude-final-readiness-review-request.md` and
  `claude-final-readiness-review-result.md`.
- [x] README/operator guide updated during implementation.
- [x] Operator guide records the tested Desktop full-backend restart
  requirement after a local plugin refresh or trust change.
- [x] Project context updated for the Codex-host phase and current release
  facts.

## Result

**BLOCKED - OPERATIONAL-CORE SECURITY CLOSEOUT REOPENED.**

Commit `89a28c22f3b901045ad3fcd03edc33257720f776` changed only the integrated
dogfood task checkbox while this verification record still stated that the run
remained pending. The remote checkpoint identifies a pushed commit, but the
packet does not yet reconcile durable proof, both verifier results, integration
evidence, and remote confirmation strongly enough to support that completion
claim. The task is reopened; absence of a located record is not reported as
proof that the underlying action did not occur.

The earlier LaunchGuardian source-build result remains useful point-in-time
evidence, but it is not an enforced candidate-bound phase in the Codex workflow.
Installed/PyPI LaunchGuardian 0.2.0 also cannot reproduce the reviewed
disposition behavior. The operational core therefore remains BLOCKED until the
candidate-bound fail-closed security gate is implemented, tested,
cross-reviewed, independently verified, and exercised with a reproducible
LaunchGuardian installation.

On 2026-07-29 the Owner re-trusted the machine-specific installed
`apply_patch` hotfix. A live current-task probe and a separately started fresh
Codex task both created and deleted an ordinary disposable file through
`apply_patch`, denied an attempted `.env` creation through the Drydock secrets
guardrail, and left both probe paths absent. The repository remained clean at
`89a28c22f3b901045ad3fcd03edc33257720f776`. This closes the tested-host
edit-bootstrap blocker; it does not make the absolute-root personal hotfix
portable or upgrade-stable.

On 2026-07-30 the local operational-core security slice added schema-v3
workflow ordering, a candidate-bound `security_review` admission, fresh
committed-tree scanning, fixed strict LaunchGuardian arguments, bounded strict
report parsing, candidate/tool/report identity evidence, post-process
Owner-checkout drift detection, admission-bound record replay prevention,
controller-side raw-evidence revalidation, and fail-closed resume behavior. A
direct caller-supplied `passed` outcome without accepted keyed evidence was
explicitly rejected in the focused tests. The scanner process is not
host-filesystem write-confined; this is detection rather than prevention, and
the local LaunchGuardian/scanner toolchain remains trusted.

Focused deterministic evidence:

- `test_orchestration_control.py`: 27 passed, 1 skipped.
- `test_orchestration_evidence.py`: 54 passed.
- `test_process_runner.py`: 75 passed.
- `test_orchestrator.py`: 55 passed.
- Combined exact post-peer-hardening run: 211 passed, 1 skipped in 150.20
  seconds.
- `python scripts/sdd.py verify codex-host-mvp`: artifacts verified, 41
  complete, 3 pending; archive remains unavailable without force.
- `git diff --check`: exit 0; Git emitted only the existing line-ending
  normalization warning for `plan.md`.

This is implementation evidence, not independent verification. Peer
cross-review, a separate verifier, a reproducible disposition-capable
LaunchGuardian installation, integrated dogfood, and the permitted lifecycle
actions remain pending.

The bounded Opus implementation cross-review run
`e0d71ae57c8d4b519aad476090ae6a28` reviewed commit `963c285...` and its exact
v2 executable fingerprint with 61,716 outbound bytes at an observed provider
cost of `$0.8440355`. It returned no blocking concern but correctly reported
`insufficient_context` and did not converge because the bounded package omitted
surrounding phase-order/admission code and real-report satisfiability evidence.
Its concrete gaps drove three local corrections: the record key now covers the
complete stored security result, accepted records have a bounded age, and the
Owner-checkout drift result is explicit rather than hardcoded. A checked-in
real `APPROVED_WITH_DISPOSITIONS` report now has a regression proving the strict
shape and aggregate invariants are satisfiable. Round 2 therefore received only
the requested bounded context plus this exact correction.

Round 2 reviewed corrected commit
`1c6c4793cfdcd084f8a4df961fc7067545b7e81a` at exact v2 fingerprint
`d8ac3e10b616eb28aa76739e853619392ea24f90ba0b857dffbf7246fb2c4adf`.
Its 55,663 outbound bytes cost `$0.726683`; the two-round run totaled 117,379
input bytes and `$1.5707185` observed provider cost. The requested
`claude-opus-5` model was observed in both rounds. The final verdict reported
`context_status: sufficient`, `converged: true`, and zero blocking concerns.
Its schema-valid packet summary is
`claude-architecture-review-round-1.json`. Peer convergence completes the
cross-review half of the remaining task; it is not independent verification or
release readiness.

The first separate Codex verifier then reviewed frozen commit
`5ab33ed308ec2b44a95f00ddace58f6e65419c5a` against accepted full-suite proof
record `3740578cd1711f3dc237715946542a8a455ea29cd87cbcd0c127f0f45c074c6f`.
The runner positively preserved HEAD and working-tree identity, exited zero,
and returned a schema-valid `BLOCKED` verdict with two blocking mechanisms and
one major cleanup defect:

- report aggregates could be reassigned between scanners while preserving only
  their total;
- a keyed technical result could be finished as caller-asserted
  `procedural_failure`, preserving candidate-dependent proof;
- timeout cleanup performed an unbounded second `communicate()` call.

That verdict is treated as a failed candidate, not as verification. The local
remediation recomputes every aggregate from the finding rows, requires every
security outcome to match a fresh candidate/admission-bound keyed record,
records procedural failure stage/process/liveness evidence before allowing a
same-candidate retry, and bounds the post-termination output drain. Regression
tests include cross-scanner aggregate reassignment, technical-to-procedural
reclassification, unavailable/timeout/malformed procedural records, and pipes
that remain open after termination. The corrected focused run reports 214
passed and 1 skipped in 143.44 seconds. A new frozen proof, peer review, and
separate verifier verdict are required; the failed verdict cannot be reused.

The first bounded Claude remediation review
`786e0794a76349f1915e56d8591b81c4` received 56,906 outbound bytes at
`$1.41089` observed provider cost and stopped non-converged because its
one-call packet omitted the exact store-precedence and timeout call-site
context. Its two stated blockers were reconciled rather than waived: source
inspection showed the timeout path already measured liveness and checkout
identity before recording, and the non-zero-exit override already applied only
to an otherwise accepted report. The follow-up nevertheless made those
measurements explicit in the stored call, added stage/process
cross-consistency, normalized empty finding gates, and added blocked-plus-
nonzero, live-process, checkout-drift, and bidirectional outcome-mismatch
regressions.

A fresh one-call peer run `211a1449507d4bf79daa600a7d42c17d` reviewed exact
commit `90aa205219f0defba1ec649d7dd025f31b8c0199` and executable fingerprint
`84b4df9b564c4418e0d42b75816f4af33d0b3be8c7d2f6e3485843a7cc714ea1`.
It received the exact source bodies the prior review requested plus the
targeted test diff. The observed `claude-opus-5` call used 53,943 outbound
bytes and `$1.087367`, returned `context_status: sufficient`,
`converged: true`, and zero blocking concerns. Its schema-valid summary is
`claude-architecture-review-round-2.json`. This closes peer cross-review only;
a fresh full-suite proof and separate verifier remain required.

A fresh proof on evidence-complete commit
`a2d48d99e5e1820f164103a939fc8d5f0400b7cc` then passed at executable
fingerprint `84b4df9b564c4418e0d42b75816f4af33d0b3be8c7d2f6e3485843a7cc714ea1`,
exit 0, no timeout, in 246.94 seconds. The separate Codex verifier preserved
the exact HEAD, working-tree digest, and candidate fingerprint, but correctly
returned `BLOCKED` on two newly located bypasses:

- official `proof-run` accepted `scope=intermediate`, while controller
  `workflow-finish` did not reload a keyed full-suite proof before advancing;
- strict report parsing allowed invented finding `source` and `status` values
  when an attacker recomputed the surrounding aggregates.

That proof and verdict belong to a failed candidate and are not reused. The
local remediation now refuses official intermediate proof before process
spawn, returns a keyed proof record, and requires the controller to reload an
exact-fingerprint, zero-exit, non-timeout `full_required_suite` record before
leaving proof. Finding source/status values are restricted to LaunchGuardian's
documented 0.2.0 producer domains. Regressions cover official intermediate
pre-spawn refusal, intermediate-key rejection at workflow finish, and invented
source/status values. The corrected focused run reports 219 passed and 1
skipped in 148.90 seconds. A new frozen proof and separate verifier are still
required; absence of a later verdict is not PASS.

No publication, release, archive, or push is authorized by this evidence.

A later full proof on commit
`56df71aed039296817f6c0b69400897c03292002` and executable fingerprint
`dfdbebb8cd4f44119ff0e49a54b5377e038afd4b9438c342f888853fc7018c1a`
passed with exact keyed record
`ef5bbad9b95253aa75f1a6c3916f232cd5a28131fe11b2a93c8dc9caf14a5b03`,
exit 0, no timeout, and 240.063 seconds elapsed. The separate Codex verifier
preserved the exact candidate state but returned `BLOCKED`: the report parser
recomputed `scanner_counts` and `scanner_blocking_counts` only when a scanner
reported `ran`. A report that relabelled Semgrep `unavailable` could therefore
carry inflated scanner totals and be treated as a candidate-preserving
procedural failure rather than rejected as contradictory evidence. That proof
and verdict remain attached to the failed candidate and are not reused.

The local remediation now validates per-scanner totals for every availability
state against LaunchGuardian 0.2.0's actual producer behavior. A `ran` scanner
binds its finding rows, `unavailable` binds one synthetic
`scanner_unavailable` row while retaining a zero detected count, failed
execution binds no scanner row and zero counts, and `disabled` binds the
scanner's named `config/scanner_disabled` row. Unknown non-running states
cannot carry scanner rows or non-zero totals. Finding title and category are
now part of the checked producer shape. Parameterized regressions inflate both
detected and blocking totals across disabled, unavailable, execution-failed,
failed, and unknown/skipped states and require fail-closed rejection.

The corrected pre-freeze focused run reports 224 passed and 1 skipped in
156.57 seconds. Root/scaffold sync remains 11/11; scaffold-bundle,
hook-runtime/definition, and release-version parity all pass; packet
verification reports 41 complete and 3 pending; and `git diff --check` exits
zero. A new clean commit, full proof, and separate verifier verdict are still
required. The earlier Claude convergence is stale for this changed executable
fingerprint, and no cross-model gate will be claimed until a fresh peer review
can run.

The separate verifier on the resulting clean commit
`a959819270b7de1018424c255efc5b225be9fa04`, executable fingerprint
`ac910167afd455b92d47dae1abc3b28f22be58b8c72015f4c21a86252f928db6`,
and accepted full-suite record
`a08e29a20b79e6436e13a3bcded428ba51eac324e6bfc04a5023525e56a9cd64`
confirmed that the every-state count defect was closed. It preserved exact
HEAD, working-tree, and candidate identity, but returned `BLOCKED` on one new
cross-field bypass: the report parser allowed an otherwise valid finding to
adopt an allowed non-open status without the exact disposition evidence the
pinned LaunchGuardian producer requires. Its read-only probe made a Critical
Semgrep row `not_applicable` without a disposition and obtained green
structural acceptance; it also converted the strict unavailable row into a
candidate-preserving procedural result. The verifier separately recorded the
already-known stale Claude review and installed schema-0.1.0 package as
non-code remaining gates.

The local remediation now validates `rule_id` and disposition fields, requires
unique exact Semgrep disposition configuration with meaningful reason,
evidence, reviewer, and non-future ISO date, rejects Critical dispositions,
and limits `needs_review` to LaunchGuardian's named unused-disposition policy
row. It also enforces the strict unavailable row's exact title, category,
source, severity, open status, blocking flag, empty rule, and absent
disposition; rejects unknown scanner states; and recomputes launch and LGF
status. Focused regressions cover both verifier probes. This is remediation
evidence only: a new frozen proof and separate verdict are required, and the
cross-model gate remains pending while Claude usage is unavailable.

The 2026-07-30 Codex-only dogfood reached candidate-bound LaunchGuardian after
one clean isolated candidate and one accepted exact-fingerprint
`full_required_suite` proof. The first security invocation correctly rejected
the installed scanner because its package metadata reported 0.2.0 while its
runtime emitted schema 0.1.0 without `counts_by_status`; it was recorded as a
procedural failure, never PASS. Clean local LaunchGuardian commit
`c754062dc1c35dce06cfc6f7946909287f1ce1fc` returned 81 passing tests and was
reinstalled without network access. The corrected schema-0.2.0 strict scan
then exposed one open High Semgrep finding:
`trailofbits.python.tarfile-extractall-traversal.tarfile-extractall-traversal`
at `fresh_proof_root`. This is a substantive security gate, so no disposition
or parser waiver was added. The remediation removes tar extraction, keeps the
archive in memory, and materializes only blob bytes and executable modes
already proven equal to the committed Git tree. A regression also proves a
committed `.archive.tar` file is retained and neither `extract()` nor
`extractall()` is invoked. The focused orchestration-evidence suite returned
`60 passed in 30.90s`; `git diff --check` and
`python scripts/sdd.py verify codex-host-mvp` returned zero, with the packet at
42 complete and 3 pending. Fresh proof, strict LaunchGuardian, separate
verification, and integration remain required on the remediated commit.

The 2026-07-30 source-contract audit compared this remediation directly with
LaunchGuardian 0.2.0 commit
`c754062dc1c35dce06cfc6f7946909287f1ce1fc`. It removed the invented
`execution_failed` availability state, requires disposed Semgrep findings to
retain the producer's severity-derived blocking flag, and requires every
configured-but-unused disposition to retain the producer's explicit
`needs_review` evidence. Negative regressions cover the invented state,
blocking-flag reclassification, and omitted unused-disposition record. The
authoritative LaunchGuardian subset returned 7 passed; the Drydock evidence
suite returned 60 passed; the complete four-file focused orchestration suite
returned 223 passed and 1 skipped in 149.38 seconds. `git diff --check`
returned exit 0. No provider, verifier, full adapter/legacy/parity suite,
commit, or push was used to obtain this evidence.

## 2026-07-30 completed Codex-only integrated closeout

- Owner-selected route: explicit Codex-only `single_pilot`. The stored plan
  omitted `plan_peer` and `cross_review`; no Claude call or Claude quota was
  used. Peer convergence remains `not_established`, and same-model process
  separation is not epistemic independence.
- Workflow objective:
  `ca7c9da1f89a084cf958a2ac2ab3579b`.
- Task ID:
  `019f9558-d3e4-77a1-b7b1-9cb7fd75233e`.
- Ordered phases:
  `preflight -> mutation -> proof -> security_review -> verification ->
  integration -> complete`.
- The first proof wrapper was recorded as a procedural failure under record
  `93adf7991f106030d86ac5256d23cc395b36cfb13b3c44d58d6a314fcb6c8852`.
  PowerShell mangled the inline Python command before any suite subprocess
  started. The failed proof was not reused. The workflow invalidated the first
  candidate and required the fresh Owner action `Resume` before continuing.
- Replacement isolated candidate:
  `3e5b8e1dcb2a2367e8d4a4424088e4ffc2ddec4a`, based on
  `52ee215da3fb1269628f3280dc14a61736f240d3`.
- The candidate changed only
  `sdd-plus/changes/codex-host-mvp/tasks.md`; its exact Git blob was
  `df5a4324ccb798aea82ecfba4eef384600e6a8c0`.
- Exact executable-surface fingerprint:
  `698ce260c71c0a6570c01e35f04f4328d589d9395c75a4ac6ccd26f982c4ea35`.
- Candidate packet-evidence fingerprint:
  `8cf40d7d4ae7e2cf62bc93a25970f88ada7a3e172938ea64ab04c2c65a2556f0`.
- Full required suite record:
  `1c4ec2346ebe99d27282b40e93213d0a1ce3933a16a2827cb3447c19b8f4b7d8`.
  The exact eight-command run covered the legacy suite, complete Codex adapter
  suite, root/scaffold sync, scaffold bundle, hook bundle, release parity,
  `codex-host-mvp` packet verification, and
  `peer-unavailable-governance` packet verification. It exited zero, did not
  time out, took `235.329` seconds, and produced output SHA-256
  `4104af468a98eac9d9906b9193e676221721786f94c25ec30c71320f64065c24`.
  The record is user-writable, unauthenticated, and does not attest execution
  provenance.
- Candidate-bound LaunchGuardian record:
  `717683b859663cdb85f0f96c9a02aa30071c9050ef3d2a9d912b7007827e3874`.
  LaunchGuardian `0.2.0` ran all five expected scanners in strict framework
  mode and returned `APPROVED` with zero blocking findings in `3.672` seconds.
  Its report SHA-256 was
  `cee7707b33514a655faf56314fe817e616baf34e7d376db2ac852146b0739a56`.
- The one separate read-only verifier used `gpt-5.6-sol` under admission
  `1f7b849b49dacf1150eb88f9f88b46756b324d8fdeef0f1ed9052fbf27752c6d`.
  It returned `PASS`, runner `ok: true`, stage `complete`, exit `0`, no
  timeout, no parse error, tree unchanged, candidate unchanged, and exact
  state binding to the candidate. Its structured-result SHA-256 was
  `40049f8170d4c79f67cc146e91ae790be5fc33a0e808d0eb4a77549979c503b6`.
  It consumed 3,585,209 input tokens, including 3,416,320 cached tokens, and
  produced 22,018 output tokens. One internal read-only Windows JSON probe
  failed on an invalid escape before the verifier completed the required
  checks by other means; this was visible in stderr and was not treated as
  positive evidence.
- Runner-owned fast-forward integration moved the Owner branch from
  `52ee215da3fb1269628f3280dc14a61736f240d3` to the exact candidate commit.
  The canonical integration-summary SHA-256 is
  `ebc314fba10986e11b150d93af871debfe6eb41eaa5d7fc30a23f627436d0a90`;
  no push occurred inside the workflow.
- Workflow terminal state: `complete`; elapsed `1062.935` seconds, one
  recorded procedural failure, and no open circuit. Trustworthy provider cost
  was unavailable and is not reported as zero.
- This evidence closes the three previously pending implementation tasks. It
  does not authorize publication or release and does not claim cross-model
  agreement.
- Non-self-inclusive packet-evidence-parent fingerprint, computed after the
  final task state and verifier record while excluding this
  `verification.md` report:
  `b9b71db9787d83270708cc16a5dd970a9565e8167d0b9949f0ddcddab16c556e`.

This closeout section supersedes the packet's earlier historical `BLOCKED`
result for the current committed implementation. Those blocked attempts remain
preserved above as failure evidence; they are not relabelled as passing.

## 2026-07-30 bounded Unicode hook-bootstrap hotfix

- [x] Regression-first proof — the two new raw UTF-8 smart-quote tests, run
  through an explicit cp1252 `TextIOWrapper`, both failed against the old
  verifier: the benign payload received a false integrity message and the
  tampered runtime returned an unidentified `systemMessage`.
- [x] Exact-byte implementation — the inline verifier reads host stdin once
  with `sys.stdin.buffer.read()`, passes `original` to the captured verified
  runtime with `io.TextIOWrapper(io.BytesIO(original), encoding='utf-8')`, and
  identifies failure events from `original.decode('utf-8')`. It still verifies
  one captured runtime read and executes those same captured bytes.
- [x] Focused regression proof —
  `python -m pytest adapters/codex/tests/test_hook_runtime.py -q -p
  no:cacheprovider` returned `16 passed in 14.13s`. The genuine runtime emitted
  no denial for the benign Unicode `apply_patch` payload, while a tampered
  runtime emitted the exact structured `PreToolUse` integrity denial and never
  executed the tampered bytes.
- [x] Deterministic checks — the explicit `build_hooks.py --check` returned
  `hook runtime and definition match source`; `python scripts/check_sync.py`
  returned all 11 root/scaffold pairs identical.
- [x] Scope and preservation — `hook_runtime_source.py`, generated
  `runtime.py`, and `runtime.manifest.json` have no diff. Both edited Python
  sources remain ASCII-only. The untracked partial
  `sdd-plus/specs/capabilities/codex-host.md` remains exactly 5,386 bytes with
  SHA-256
  `d882f58a32b172a814f86987bad1c780e6c036eeb177a6f796e2fd96c70acbea`.
  No Claude call, new packet, spec sync, archive, personal-plugin mutation, or
  push occurred.
