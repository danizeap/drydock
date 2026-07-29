# Capability: codex-conductor

Capability: codex-conductor

## Purpose

The read-only multi-agent bridge (`scripts/conductor/codex_bridge.py`). It lets Drydock (the conductor) discover the locally-installed Codex core, read Codex's remaining quota, choose a model from that fuel, and delegate a bounded analysis/review task to Codex with schema-locked JSON output — for Claude to independently audit. It is **read-only by construction**: no code path mutates the repository, and secret-bearing content is refused before it leaves the machine. Mutating delegation is a separate concern (`codex-enforcement-bridge`). Proven live-fire on 2026-07-23 (see `sdd-plus/specs/multi-agent-orchestration-vision.md` §8).

## Requirements

### Requirement: Core discovery tracks the current install, never the stale binary
The conductor SHALL locate the Codex core by discovering the newest `codex.exe` under `%LOCALAPPDATA%\OpenAI\Codex\bin\*\`, and SHALL NOT use the `~/.codex/.sandbox-bin` copy. `discover_core()` returns a path on success and `None` when absent; absence SHALL NOT raise, and the orchestration layer surfaces it as a structured `{ok:false, stage:"discover"}`.

#### Scenario: Newest core wins
- **WHEN** two core binaries exist under the bin dir with different modification times
- **THEN** discovery returns the path of the most recently modified one

#### Scenario: Sandbox binary is never returned
- **WHEN** a `codex.exe` exists only under a `.sandbox-bin` path
- **THEN** discovery does not return it (it is outside the discovery root)

#### Scenario: Absence is structured, not an exception
- **WHEN** no core is found under the discovery root
- **THEN** `discover_core()` returns `None` without raising

### Requirement: The fuel gauge is read safely and always cleans up
Reading Codex quota SHALL return a structured result in every case and SHALL NOT leak the `app-server` subprocess.

#### Scenario: Successful read
- **WHEN** the gauge is read successfully
- **THEN** the result is `{ok:true, result:{...rateLimits...}}` including `primary.usedPercent` and `resetsAt`

#### Scenario: Operational failure is structured and reaped
- **WHEN** `app-server` fails to spawn, exits early, closes stdout, or does not respond within the timeout
- **THEN** the result is `{ok:false, stage, error, stderr}` — never a traceback — and the subprocess is terminated and reaped

#### Scenario: Non-object protocol line ignored
- **WHEN** a non-object JSON line appears on the protocol stream
- **THEN** it is ignored rather than crashing the reader

### Requirement: Delegation is structurally read-only
`delegate()` SHALL run Codex with a fixed safety flag set that no caller input can override, SHALL validate the model identifier as a bare token, and SHALL have no code path that writes into the repository.

#### Scenario: Read-only flags always present, escalation flags never
- **WHEN** any delegation argv is built
- **THEN** it contains `-s read-only` and none of `--dangerously-bypass-approvals-and-sandbox`, `workspace-write`, or `danger-full-access`

#### Scenario: Only prompt/schema/model/cwd are caller-controlled
- **WHEN** a caller invokes delegation
- **THEN** sandbox mode, ephemerality, and git-check flags are fixed by the conductor; the prompt is passed via stdin, never as argv

#### Scenario: Flag-shaped model refused
- **WHEN** the model identifier is not a bare token (e.g. contains a space or a leading `-`)
- **THEN** delegation is refused with `{ok:false, stage:"bad_model"}` before any spawn

#### Scenario: No repository mutation
- **WHEN** a delegation completes
- **THEN** the working root is a fresh temp dir that is cleaned up, and no file under the repository is created or modified

### Requirement: Secrets never leave the machine via delegation
The conductor SHALL refuse to delegate content whose source path is secret-bearing, reusing `hooks/protect_secrets.path_is_secret`, and SHALL fail closed if that checker cannot be loaded.

#### Scenario: Secret path refused before spawn
- **WHEN** `delegate_file` is asked to include content from a secret-bearing path (`.env`, key/credential files)
- **THEN** it returns `{ok:false, stage:"secret_guard"}` before reading the file or spawning Codex

#### Scenario: Ordinary file proceeds
- **WHEN** the content source is an ordinary project file
- **THEN** delegation proceeds

#### Scenario: Fail closed when the checker is unavailable
- **WHEN** the secret-path checker cannot be imported
- **THEN** `guard_outbound` refuses all delegation rather than egressing unchecked

### Requirement: Routing is a legible, fuel-aware policy
Model selection SHALL be a documented function of task weight and remaining Codex fuel.

#### Scenario: Heavy task with fuel above the floor
- **WHEN** the task is heavy and remaining fuel is above the conserve floor (15%)
- **THEN** the flagship model is selected

#### Scenario: Heavy task at or below the floor
- **WHEN** the task is heavy but fuel is at or below the floor
- **THEN** a workhorse model is selected to conserve the tank

#### Scenario: Light task
- **WHEN** the task is light
- **THEN** a workhorse model is selected regardless of fuel

### Requirement: No live quota spent by the test suite
Automated tests SHALL prove the above without invoking the real Codex service; any live smoke test SHALL be opt-in and excluded from CI.

#### Scenario: CI spends no quota
- **WHEN** the test suite runs in CI
- **THEN** it uses a fake Codex stand-in (invoked through the real subprocess path) and spends no account quota

#### Scenario: Live test is opt-in
- **WHEN** a developer sets `DRYDOCK_CODEX_LIVE=1`
- **THEN** a single real round-trip may run locally; otherwise it is skipped

### Requirement: In-session review CLI with structured outcomes
`scripts/conductor/review.py` SHALL delegate a read-only review of one or more files to Codex and print a structured JSON result for EVERY outcome — never a bare traceback. It SHALL reuse the conductor primitives, refuse secret-bearing paths (given paths AND their realpaths), frame file content as untrusted data (prompt-injection defense), and enforce per-file and total byte caps.

#### Scenario: Ordinary file reviewed
- **WHEN** the target is an ordinary file and Codex is available
- **THEN** the CLI prints `{ok: true, gauge, route, delegation.result}` and exits 0

#### Scenario: Secret path refused (incl. via realpath)
- **WHEN** a target path or its realpath is secret-bearing
- **THEN** the CLI prints `{ok: false, stage: "secret_guard"}` and sends nothing

#### Scenario: Every failure is structured
- **WHEN** Codex is absent, a file is missing, exceeds the size cap, or a read fails
- **THEN** the CLI prints `{ok: false, stage: "discover"|"missing_file"|"too_large"|"read_error"}` rather than raising

### Requirement: The review command audits, never rubber-stamps
The `/drydock:codex-review` command SHALL treat Codex's findings as input to an independent audit (confirm/refute/refine + additions from wider context), present a synthesis with Codex's remaining fuel noted, never send secret-bearing files, and never modify the repository.

#### Scenario: Findings are audited before presentation
- **WHEN** Codex returns findings
- **THEN** Claude verifies each (CONFIRM/REFUTE/REFINE) before presenting, and Codex's output is never treated as authoritative

### Requirement: Mutating delegation is isolated to a worktree, never the base branch
`scripts/conductor/mutate.py` SHALL run Codex with sandbox `workspace-write` confined to a dedicated worktree on a fresh `codex/…` branch from `base`. It SHALL NOT write to the Owner's branch or working tree, and SHALL be the only conductor path that enables writes (the read-only `delegate()` lock is unchanged).

#### Scenario: Writes are contained
- **WHEN** a mutating task runs
- **THEN** Codex's changes appear only in the isolated worktree/branch; the base branch HEAD is unadvanced and the main working tree is unmodified

### Requirement: The merge gate is applicability-first; N/A is never a failure
Before pass/fail, the gate SHALL decide whether it applies. Docs/config-only → test gate N/A (clean pass). Code/behavior change → green tests required (red or not-run is a hard block). N/A SHALL be distinct from FAIL.

#### Scenario: Docs-only is N/A
- **WHEN** the change touches only docs/config
- **THEN** the verdict is `n/a` with `clears: true` — not a failure

#### Scenario: Code needs green
- **WHEN** the change touches code and tests are red or were not run
- **THEN** the verdict is `red`/`blocked` with `clears: false`

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

### Requirement: Advisories inform, never gate
The gate SHALL emit an `advisories` list — including a coverage-gap note when the diff changes code with no test file, and a disclosure when the command delegates to a script runner — and advisories SHALL NEVER affect `verdict` or `clears`.

#### Scenario: Advisory does not change the decision
- **WHEN** an advisory is present
- **THEN** the verdict and `clears` are identical to the same result without it

### Requirement: Handoff separates in-flight work; results name the path
`gather_state()` SHALL report `packets` (all un-archived) and `in_flight_packets` (unchecked tasks or an unfilled verification); the `write` result SHALL include a `path` field.

#### Scenario: A finished packet is not in-flight
- **WHEN** a completed packet sits un-archived under `sdd-plus/changes`
- **THEN** it appears in `packets` but not in `in_flight_packets`

### Requirement: Review findings identify their file
Each review finding SHALL carry the `file` it refers to, so multi-file reviews can be triaged.

#### Scenario: Multi-file review is triageable
- **WHEN** several files are reviewed in one run
- **THEN** every finding names its file

### Requirement: No auto-merge; structured verdict for review
`mutate.py` SHALL NEVER merge. It SHALL return `{worktree, branch, diff, files, tests, gate, clears_gate, merged: false, note}` for Claude to review and merge deliberately; clearing the gate is necessary, not sufficient. Every outcome SHALL be structured (no bare traceback).

#### Scenario: Nothing merges automatically
- **WHEN** a mutating delegation completes
- **THEN** the result reports `merged: false` and carries the diff + gate verdict; the worktree is kept when reviewable and cleaned up on empty/failed delegation

### Requirement: Cleanup is blast-radius-bounded
Worktree cleanup SHALL remove only the temp worktree and a branch whose name begins with `codex/`; it SHALL never delete any other branch.

#### Scenario: Non-codex branch is safe
- **WHEN** cleanup is asked to delete a non-`codex/` branch
- **THEN** that branch is left intact

### Requirement: Pluggable executors with a proven/staged distinction
The conductor SHALL expose executors through a common interface (`available`, `read_remaining`, `status`), with `CodexExecutor` verified (wrapping `codex_bridge`) and additional executors (e.g. `KimiExecutor`) staged. `available()` (presence) SHALL be separate from `verified` (proven on this machine).

#### Scenario: Codex reads real fuel
- **WHEN** `CodexExecutor` runs where a Codex core is discoverable
- **THEN** it reports available + verified and reads real remaining fuel

### Requirement: A staged executor can never run or be reported usable
An unverified executor SHALL NOT appear in the fleet `usable` set and SHALL refuse to read fuel or execute, EVEN IF present on the machine.

#### Scenario: Present-but-unverified is staged, not usable
- **WHEN** a staged executor (Kimi) is present but unverified
- **THEN** it is reported `staged`, never `usable`, and its run/read path raises `ExecutorUnverified`

### Requirement: Honest fleet status + Owner-chosen stack
`fleet_status()` SHALL list Claude (the conductor) separately as human-tracked (its quota is not machine-readable), report each executor's usable/staged state, and honor an Owner-configured stack (`DRYDOCK_EXECUTORS`) defaulting to auto-detection (Claude alone / +Codex / +Kimi / all three).

#### Scenario: Stack is configurable
- **WHEN** `DRYDOCK_EXECUTORS=codex`
- **THEN** only Codex is considered; Claude remains the human-tracked conductor

### Requirement: Deterministic, read-only handoff state
`handoff.py::gather_state()` SHALL capture — without mutating the repo — the branch, HEAD, active change packets, open `codex/` worktrees, and the executor `fleet_status()`. Read failures SHALL degrade to benign values, never a traceback.

#### Scenario: State is gathered read-only
- **WHEN** `gather_state()` runs
- **THEN** it returns branch/HEAD/active packets/open codex worktrees/fleet and makes no changes

### Requirement: HANDOFF.md relay, re-verified on the way in
`write_handoff()` SHALL render a fixed-shape `HANDOFF.md` (where-we-are / fleet fuel / next step / notes) where only the next step + notes are human-supplied; `read_handoff()` returns it or None. The `/drydock:handoff` command SHALL instruct the incoming leader to reconstruct from live reality — HANDOFF.md never overrides `git`/`sdd.py status`.

#### Scenario: Incoming leader re-verifies
- **WHEN** a leader writes a handoff and another resumes from it
- **THEN** HANDOFF.md carries deterministic state + a one-line next step, and the incoming leader re-verifies against reality before acting

### Requirement: Fuel-aware fleet advice; Claude human-tracked
`fleet_recommendation()` SHALL list each usable tank's fuel/reset, flag a low tank (`<15%`), prefer spending the tank closest to its reset (protect the far one), and always note Claude as human-tracked.

#### Scenario: Spend the near-reset tank
- **WHEN** two tanks are usable with different reset horizons
- **THEN** the advice prefers spending the nearer-reset tank and protecting the other; Claude is noted as human-tracked

### Requirement: Shared, single-flight gauge cache; fail-open always
`coord.get_gauge(executor, ttl)` SHALL serve a per-tank gauge from a TTL cache within the window, best-effort single-flight refresh when stale (N concurrent chats collapse to ~1 real read per TTL), and fall back to a direct `executor.read_remaining()` on ANY error, on `DRYDOCK_COORD_DISABLE=1`, or when the state dir is unavailable. It SHALL NOT raise into or block a delegation.

#### Scenario: Two reads share one refresh
- **WHEN** the gauge is read twice within the TTL
- **THEN** the first is a real read (`source: fresh`), the second is served from cache (`source: cache`) with no second real read

#### Scenario: Any failure falls back to a direct read
- **WHEN** the underlying read raises, coord is disabled, or the state dir can't be created
- **THEN** `get_gauge` returns a direct read and never raises

### Requirement: Only real numbers, honestly aged; never a fabricated reservation
The cache SHALL store only successful reads and serve real values tagged with `source` + `as_of_age_s`, adjusting the reset countdown by cache age (clamped at 0), and SHALL NOT invent a reserved/allocated fuel percentage.

#### Scenario: Aged serve is honest
- **WHEN** a cached gauge is served after aging
- **THEN** `resets_in_hours` is reduced by the cache age (never below 0) and the age is surfaced; no value is fabricated

### Requirement: No deadlock; state off shared/synced trees; isolated in tests
The single-flight lock SHALL be stealable once older than a threshold above the read timeout (a crashed holder never deadlocks). State SHALL live outside `~/.codex` and OneDrive-synced trees. A corrupt/wrong-shape cache SHALL self-heal (treated as absent). Tests SHALL never write the real coordination state dir.

#### Scenario: Stale lock is stealable, fresh lock defers
- **WHEN** a refresh lock is older than the stale threshold
- **THEN** another session may steal it and refresh; a fresh lock instead defers to serve slightly-stale cache

### Requirement: Review what changed, discovered honestly
`review.py --diff [--base <ref>]` SHALL review the CURRENT CONTENT of files changed in the working tree (vs HEAD, including untracked) or vs an explicit base, and SHALL report deleted paths separately. Path listing SHALL be NUL-delimited (git C-quotes unusual paths) and SHALL resolve against the repository root, so a run from a subdirectory cannot report a false clean. A git failure SHALL be reported as an error — **never** as an empty change set.

#### Scenario: Modified and untracked both appear
- **WHEN** files are modified and new files are untracked
- **THEN** both appear in the reviewed set, while binaries/generated files (`.png`, `.lock`, `.min.js`, …) are excluded and disclosed in `skipped_not_reviewable`

#### Scenario: A status filter cannot hide a type change
- **WHEN** a tracked file's TYPE changes (e.g. a regular file replaced by a symlink) or a file is unmerged
- **THEN** it appears in the changed set — a status filter SHALL NOT drop it into "no changes"

#### Scenario: Discovery from a subdirectory is not a false clean
- **WHEN** `--diff` runs from a subdirectory while tracked files changed at the repository root
- **THEN** those changes are found — an empty set SHALL NOT be reported without a git failure

#### Scenario: Deletions are reported, subject to the secret guard
- **WHEN** files were deleted in the change
- **THEN** their paths are reported to the Owner, and named to the reviewer **except where the outbound guard withholds them** — a secret-bearing deleted path is disclosed to the Owner and never sent

#### Scenario: A git failure is never silence
- **WHEN** the git query fails (e.g. an invalid `--base`)
- **THEN** the result is `stage: git_error` — not "no changes"

### Requirement: Auto-discovery never widens what leaves the machine
For an auto-discovered set the tool SHALL skip-and-disclose (never send) any path that is secret-bearing **by name**, whose **content** matches high-confidence secret material, or whose realpath resolves **outside the repository**. An **explicitly named** secret path (by name or content) SHALL be refused outright. Where containment **cannot be established**, the tool SHALL fail closed. Paths sent to the reviewer SHALL be repo-relative where they resolve inside the repository. No skip SHALL be silent — **every** outcome, success or failure, SHALL carry the skip lists.

#### Scenario: Secret by name or by content is skipped
- **WHEN** a changed file is secret-bearing by name or contains secret material
- **THEN** it is skipped, listed in `skipped_secret`, and never sent

#### Scenario: Out-of-repository paths are skipped
- **WHEN** a changed path is a symlink resolving outside the repository
- **THEN** it is skipped and listed in `skipped_outside_repo`

#### Scenario: An explicit secret path is refused, not skipped
- **WHEN** the operator explicitly names a secret-bearing path
- **THEN** the run is refused (`secret_guard` / `secret_content`) rather than silently skipped

#### Scenario: Unverifiable containment fails closed
- **WHEN** the repository root cannot be determined during auto-discovery
- **THEN** the run is refused (`stage: no_repo_root`) — containment is unverifiable, so nothing is sent

#### Scenario: An early failure is still an outcome
- **WHEN** the run ends in an error stage (`too_large`, `read_error`, `discover`, …) after files were skipped
- **THEN** the skip lists are still present in the result

#### Scenario: Everything filtered means nothing sent
- **WHEN** every candidate is filtered out
- **THEN** the result is `stage: nothing_to_review` with the skip lists populated

### Requirement: Nothing reviewed can escape its delimiter
The prompt SHALL delimit every untrusted region with a boundary marker absent from **all** interpolated text — file content **and** file paths (escalated until unique) — so neither a file nor a *file name* can close its own fence and reach the instruction region. Deleted paths are untrusted data and SHALL be delimited, not placed in the instruction region. Any git ref accepted from the operator SHALL be validated before it reaches a git argv. Every outcome other than `--help` SHALL be structured JSON on stdout with nothing on stderr, and an invocation that would silently discard operator-specified scope SHALL be refused.

#### Scenario: Content or path bearing the marker escalates it
- **WHEN** a reviewed file's content or its **path** contains the boundary marker text
- **THEN** the marker escalates so neither can close it

#### Scenario: A deleted file name is data, not instruction
- **WHEN** a change deletes a file whose name reads as an instruction
- **THEN** the name appears inside a delimited data region, never in the preamble

#### Scenario: An option-shaped ref never reaches git
- **WHEN** `--base` is option-shaped (e.g. `--output=<path>`)
- **THEN** it is refused as `bad_arguments` before git runs, so it cannot make git write a file

#### Scenario: Argument errors keep the JSON contract
- **WHEN** the CLI is invoked with invalid arguments
- **THEN** it emits `stage: bad_arguments` as JSON rather than bare usage text, and writes **nothing** to stderr — a caller merging the streams still receives valid JSON

#### Scenario: Scope is never silently discarded
- **WHEN** flags are combined such that operator-specified scope would be ignored (`--diff` with paths, `--base` without `--diff`)
- **THEN** the run is refused as `bad_arguments` rather than silently discarding the scope

### Requirement: Plan negotiation is a read-only peer critique
`negotiate.py` SHALL send an implementation plan to Codex as an equal peer and return a schema-locked critique — an honest overall take, a `converged` flag, `blocking_concerns`, `gaps`, `risks`, and a `decomposition` proposing per-task owner (claude/codex/either) and model tier (flagship/workhorse/cheap). It SHALL be read-only, SHALL frame the plan as data behind a boundary marker the content cannot close, and SHALL refuse to send a plan that is empty or appears to contain secret material — before Codex is spawned.

#### Scenario: A real plan yields a fuel-routed critique
- **WHEN** a real plan is negotiated
- **THEN** Codex returns a structured critique routed to a fuel-appropriate model, and the critique is the pilot's input to audit — never authoritative

#### Scenario: Empty or secret-bearing plans are refused before spawn
- **WHEN** the plan is empty or looks secret-bearing
- **THEN** the run is refused (`empty_plan` / `secret_content`) and no plan is sent

#### Scenario: A plan cannot close its own fence
- **WHEN** the plan text contains the boundary marker
- **THEN** the marker escalates so the plan cannot close its own fence

### Requirement: The negotiation loop is bounded and terminates
A pure `loop_should_continue(critique, round, cap)` SHALL decide whether to negotiate another round, and SHALL stop when Codex has genuinely converged (the `converged` flag AND no blocking concerns) or the round cap is reached. The cap SHALL be the hard stop that prevents the two brains from consuming flagship tokens indefinitely. A `converged` flag that still lists blocking concerns SHALL NOT be trusted.

#### Scenario: Genuine convergence stops the loop
- **WHEN** Codex reports converged with no blocking concerns
- **THEN** the loop stops — both brains agree

#### Scenario: Blocking concerns continue the loop
- **WHEN** blocking concerns remain and the cap is not reached
- **THEN** the loop continues for another round

#### Scenario: The cap is an absolute ceiling
- **WHEN** the round cap is reached
- **THEN** the loop stops regardless of remaining concerns — the pilot decides

#### Scenario: A contradictory converged flag is not trusted
- **WHEN** Codex reports `converged: true` but still lists blocking concerns
- **THEN** the contradiction is not trusted and the loop does not treat it as converged
