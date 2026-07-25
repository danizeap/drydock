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
- [ ] Final Opus convergence — the first exact-Opus-5 high-effort review
  refused before spawn because the outbound secret scanner matched a synthetic
  fixture. After exact fixture redaction, the full bundle exited
  `error_max_budget_usd` at the $1.25 ceiling without a critique. A focused
  retry and a still-smaller blocker-only retry each reached their 300-second
  timeout without a critique. Every returned peer status still reported
  first-party authentication ready and requested model `claude-opus-5`; none
  reported Fable quota exhaustion or model unavailability. These outcomes are
  not agreement, rejection, or evidence about the code.
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
- [x] Final packet consistency refresh — `python scripts/sdd.py verify
  codex-host-mvp` reports `32 complete, 2 pending`; the pending final peer and
  dogfood gates remain explicit.

## Documentation Updates

- [x] `docs/CODEX_HOST_BUILD_BLUEPRINT.md` added.
- [x] Change packet brief, plan, tasks, decisions, and verification populated.
- [x] Delta specs added for Codex host behavior, orchestration, and enforcement.
- [x] Cross-model blocking review reconciled into the blueprint and packet.
- [x] A bounded re-review prompt is saved as `claude-rereview-request.md`.
- [x] README/operator guide updated during implementation.
- [x] Project context updated for the Codex-host phase and current release
  facts.

## Result

**IMPLEMENTATION AND SECURITY-SCAN EVIDENCE PASS — FINAL PEER AND DOGFOOD
GATES OPEN.**

The additive plugin, deterministic enforcement adapter, peer controller,
mutation runner, and verifier pass their local suites and current-machine live
probes. The latest Opus findings were implemented, but two bounded final-review
attempts emitted no critique, so cross-model convergence remains unproven.
LaunchGuardian's reviewed source build returns
`APPROVED_WITH_DISPOSITIONS` with 0 open blockers while retaining all six High
findings; PyPI 0.2.0 cannot yet reproduce that result. Ordinary Codex hook
enforcement also remains inactive until the Owner installs/trusts the plugin
and starts a fresh task with current-revision liveness. No publication or
release is authorized by this evidence.
