# Capability: codex-enforcement-bridge

Capability: codex-enforcement-bridge

## Purpose

Drydock's deterministic deny-guards (destructive git + secret-bearing writes) enforce under **Codex**, not only inside Claude Code, plus an agent-agnostic **git pre-commit** backstop. A scaffolded `.codex/hooks/drydock_guard.py` dispatcher (`assets/project-scaffold/.codex/`) resolves the installed Drydock plugin's `hooks/` and reuses `git_safety` + `protect_secrets` unchanged — Codex's hook payload is Claude-compatible (`tool_name` + `tool_input`; shell command as `tool_input.command`). It denies via Codex's `permissionDecision: deny` protocol (exit 0) and **fails open on any error**. Scope is the stateless critical floor; `packet_guard` and mutating-workflow governance are out of scope.

### Known limitations (v1)
- Native `apply_patch` is covered; a patch smuggled through a shell command (heredoc) is caught only by the git hook at commit time, not at write time.
- A pure-Codex install (no plugin) cannot reach the guards → the dispatcher fails open; the git pre-commit hook remains the secrets backstop.

## Requirements

### Requirement: Codex deny-guards fire via the JSON protocol
The `.codex/` dispatcher SHALL run on Codex `PreToolUse` for shell tools, `apply_patch`, and file-edit tools, and SHALL deny a destructive-git or secret-write action by emitting `hookSpecificOutput.permissionDecision: "deny"` on stdout with exit 0, reusing the plugin's `git_safety`/`protect_secrets` (single source of truth). Edit-path detection SHALL be case-robust.

#### Scenario: Destructive git denied
- **WHEN** Codex issues `{"tool_name":"Bash","tool_input":{"command":"git reset --hard HEAD~3"}}`
- **THEN** the dispatcher emits a JSON `permissionDecision: deny` and exits 0

#### Scenario: Secret write via shell denied
- **WHEN** Codex issues `echo K=V > .env` or PowerShell `Set-Content -Path .env -Value ...`
- **THEN** the dispatcher denies via the JSON protocol

#### Scenario: Native apply_patch secret creation denied
- **WHEN** Codex issues an `apply_patch` adding/updating a secret-bearing file (`*** Add File: .env`)
- **THEN** the dispatcher denies via the JSON protocol

### Requirement: Benign actions and reads pass silently
The dispatcher SHALL produce no output and exit 0 for actions that are not destructive-git and do not write a secret path (including secret reads).

#### Scenario: Benign or read passes
- **WHEN** Codex issues `ls -la`, `cat .env` (a read), a `Write` to `src/app.py`, or an `apply_patch` adding `notes.txt`
- **THEN** the dispatcher exits 0 with no output

### Requirement: Fail open, never brick a session
The dispatcher SHALL exit 0 with no output on ANY error — malformed input, non-dict payload/tool_input, unresolvable plugin, or a guard exception.

#### Scenario: Malformed input fails open
- **WHEN** the stdin payload is not valid JSON
- **THEN** the dispatcher exits 0 with no output

#### Scenario: Unresolvable plugin fails open
- **WHEN** the Drydock plugin cannot be resolved (pure-Codex install)
- **THEN** the dispatcher exits 0 with no output (the git pre-commit hook remains the secrets backstop)

### Requirement: Agent-agnostic git pre-commit backstop
A git `pre-commit` hook SHALL block committing a staged secret-bearing file, firing for Codex, Claude Code, AND a human `git commit`. It SHALL be self-contained (plugin `path_is_secret` or an inline fallback with no drift from `protect_secrets._SECRET`). Fail-mode: cannot-list-staged-files fails OPEN (never brick committing); secret-detection failure fails CLOSED (block).

#### Scenario: Staged secret blocked
- **WHEN** a `.env`/key/credential file is staged and `pre-commit` runs
- **THEN** it exits non-zero and names the offending file

#### Scenario: Ordinary file allowed
- **WHEN** only ordinary files (e.g. `README.md`) are staged
- **THEN** `pre-commit` exits 0

### Requirement: Installed by init, gated on `.git/` changes
`/drydock:init-project` SHALL copy the `.codex/` bridge and offer to install the git hook, requiring Owner approval before writing under `.git/hooks/` and never overwriting an existing `pre-commit`.

#### Scenario: Init wiring
- **WHEN** init runs in a project
- **THEN** the `.codex/` bridge is copied and the git-hook install is offered with an explicit Owner-approval gate on `.git/hooks/`

### Requirement: Every mutating run reports what it cost
`mutate()` SHALL report the cost of the delegation: Codex-reported token counts where available, and the **fuel-gauge delta across the run as the authoritative figure**. Any quantity that cannot be measured SHALL be reported as `null` — never as zero, and never estimated.

#### Scenario: Codex reports usage and both gauge reads succeed
- **WHEN** Codex reports usage and both gauge reads succeed
- **THEN** the result carries token counts and `fuel_used_percent`, the difference between the before and after readings

#### Scenario: Usage is absent, malformed, or a gauge read fails
- **WHEN** usage is absent, malformed, or a gauge read fails
- **THEN** the affected fields are `null` — a cost report that invents a number would have the Owner budget against a fiction

#### Scenario: Window reset mid-run
- **WHEN** the quota window resets mid-run, so the after-reading is lower than the before-reading
- **THEN** `fuel_used_percent` is `null` rather than a negative or wrapped value

### Requirement: File scoping is opt-in and SOFT
`--files` SHALL be optional; omitting it SHALL leave delegation behavior unchanged. When given, the named targets' current content SHALL be inlined into the task so Codex need not search for them, and Codex SHALL remain free to edit files outside that set. Edits outside the declared scope SHALL be **disclosed**, never silently permitted and never blocked.

#### Scenario: `--files` is omitted
- **WHEN** `--files` is omitted
- **THEN** the prompt is the operator's task verbatim and no scope is reported

#### Scenario: Files are named
- **WHEN** files are named
- **THEN** their content is inlined behind a boundary marker no content or path can close, and the prompt states that coupled files may still be edited

#### Scenario: Codex edits a file outside the declared set
- **WHEN** Codex edits a file outside the declared set
- **THEN** the result lists it in `scope.out_of_scope` and an advisory names it — the change is not blocked, because the coupled files an operator forgets to name are exactly the ones that make a change complete

#### Scenario: A declared file is never touched
- **WHEN** a declared file is never touched
- **THEN** it is reported in `scope.declared_untouched`

### Requirement: Naming a file for inlining cannot leak a secret
A file named for inlining has its content sent off-machine, so it SHALL receive the same treatment an explicitly named review path receives: the name guard SHALL be applied to the **resolved** path as well as the given one, the path SHALL resolve **inside the worktree**, and a target that is secret-bearing **by name** or whose **content** matches high-confidence secret material SHALL cause the run to be refused **before Codex is spawned**. Size SHALL be taken from the same handle the content is read from, and both the per-file size, the total size, and the **number of names** SHALL be capped.

#### Scenario: A named target is secret-bearing by name or by content
- **WHEN** a named target is secret-bearing by name or by content
- **THEN** the run is refused (`stage: scope_guard`) and no delegation process is started

#### Scenario: Symlink alias under an innocent name
- **WHEN** a named target reaches a secret file through a **symlink** under an innocent name
- **THEN** the resolved path is guarded too, so the alias is refused

#### Scenario: The alias is a **hardlink**
- **WHEN** the alias is a **hardlink**
- **THEN** it is NOT caught — a hardlink has no target, so no path-resolution guard can see through it. This is a **stated limit**, shared with `review.py`, not a covered case

#### Scenario: Target outside the worktree, or absolute
- **WHEN** a named target resolves outside the worktree (e.g. `../../secrets.txt`) or is an absolute path
- **THEN** the run is refused — `--files` takes repo-relative paths and cannot be used to read arbitrary files

#### Scenario: Per-file, total, or name-count cap exceeded
- **WHEN** the named targets exceed the per-file cap, the total inline budget, or the maximum number of names
- **THEN** the run is refused with guidance to name fewer files or omit `--files`

#### Scenario: A file grows between the size check and the read
- **WHEN** a file grows between the size check and the read
- **THEN** the read is hard-capped and the run is refused rather than inlining past the limit

#### Scenario: A named target does not exist yet
- **WHEN** a named target does not exist yet
- **THEN** it is still passed as in-scope — it may be the file to create

### Requirement: Say when the deterministic gate is weak evidence
The result SHALL describe the diff's **shape** — file count and a **measured** cross-file repetition of added-line structure — and SHALL raise a non-gating advisory when a diff is both wide and divergent, because a passing test suite is weakest exactly there. Repetition SHALL be reported as `null` when it could not be measured, and a shape SHALL NOT be reported as repetitive on the basis of an absent measurement. **No text a delegate can write into a changed file SHALL alter which file the surrounding lines are attributed to** — the party under review cannot suppress or redirect its own advisory. The advisory SHALL NOT change the gate verdict; thresholds and the number of files actually compared SHALL be reported alongside the measurement.

#### Scenario: Mechanical sweep is not flagged
- **WHEN** many files change with structurally similar additions (a mechanical sweep)
- **THEN** `repetition` is a measured value at or above the stated threshold, `compared_files` is at least 2, the shape is `wide-repetitive`, and no advisory is raised

#### Scenario: Many files change with structurally dissimilar additions
- **WHEN** many files change with structurally dissimilar additions
- **THEN** `repetition` is a measured value below the threshold, the shape is `wide-divergent`, and an advisory states that the diff is a set of separate judgment calls needing a real read

#### Scenario: Unmeasurable repetition is unknown, not reassuring
- **WHEN** repetition cannot be measured (deletion-only, binary, or unparseable diff)
- **THEN** `repetition` is `null`, the shape is `unknown` rather than `wide-repetitive`, and an advisory states the signal is unavailable — an absence of evidence SHALL NOT read as reassurance

#### Scenario: Added content cannot hijack the parser
- **WHEN** an added line's own text resembles a diff header (e.g. `++ b/x.py`), with further changed lines following it in the same file
- **THEN** it is consumed as file content, no phantom file appears, and **every** changed file is still attributed its own lines (`compared_files` is unchanged) — the reviewed party cannot suppress or redirect its own advisory

#### Scenario: The comparison is bounded for cost
- **WHEN** the comparison is bounded for cost
- **THEN** the result says so (`sampled`, `compared_files`) rather than presenting a partial measurement as complete

#### Scenario: Any diff-shape advisory is raised
- **WHEN** any diff-shape advisory is raised
- **THEN** `verdict` and `clears` are exactly what they would have been without it

### Requirement: Cost is reported at the resolution it was actually measured
The per-task cost SHALL treat **token counts as the primary signal** (they have resolution at task scale) and the **fuel-gauge delta as a coarse window-drain signal**. When the gauge did not move measurably but tokens were spent, `fuel_used_percent` SHALL be `null` with a stated reason — it SHALL NOT report `0`, which reads as "free." A genuine no-op (no tokens spent) is not a sub-resolution cost. Fuel fields SHALL be named so their polarity (used, not remaining) is unambiguous.

#### Scenario: A task spends tokens but moves the weekly gauge by less than its r…
- **WHEN** a task spends tokens but moves the weekly gauge by less than its resolution
- **THEN** `fuel_used_percent` is `null` and `fuel_resolution` says "below gauge resolution" — never `0`

#### Scenario: The quota window resets mid-run (after-reading below before-readin…
- **WHEN** the quota window resets mid-run (after-reading below before-reading)
- **THEN** `fuel_used_percent` is `null` and `fuel_resolution` says "window reset"

#### Scenario: The run spent no tokens and the gauge did not move
- **WHEN** the run spent no tokens and the gauge did not move
- **THEN** this is a true no-op, not flagged as sub-resolution

### Requirement: Scoping caps do not fall below real files, and do not drift from review
The `--files` inline caps (per-file and total) SHALL equal the `--diff` review caps, so a file that is reviewable is also scopable and the two paths cannot diverge.

#### Scenario: A named target is up to the shared per-file cap (e.g. a 90KB sourc…
- **WHEN** a named target is up to the shared per-file cap (e.g. a 90KB source file)
- **THEN** it is inlined, not refused

#### Scenario: The review caps change
- **WHEN** the review caps change
- **THEN** the scoping caps change with them (one source of truth)

### Requirement: A timed-out delegation is recoverable, never green
On delegation timeout, any work already written to the worktree SHALL be preserved: the worktree is kept, the result is flagged `partial`, and a partial run SHALL NOT clear the gate regardless of test outcome, because incomplete work is not verified work. A timed-out run that produced no changes SHALL be cleaned up. The delegation timeout SHALL be operator-adjustable within a clamped range.

#### Scenario: A delegation times out after Codex wrote changes
- **WHEN** a delegation times out after Codex wrote changes
- **THEN** the worktree is kept, `partial` is true, `clears_gate` is false, and the note says INCOMPLETE

#### Scenario: A delegation times out having written nothing
- **WHEN** a delegation times out having written nothing
- **THEN** the empty worktree is cleaned up

#### Scenario: The operator raises `--timeout`
- **WHEN** the operator raises `--timeout`
- **THEN** it is honored within a clamped range (a sweep over a large file gets the time it needs)

### Requirement: Orphaned worktrees are recoverable, blast-radius-bounded
A garbage-collection path SHALL remove orphaned `codex/` worktrees that hold no salvageable work, SHALL keep and report ones that hold work — **uncommitted changes OR commits unique to the codex branch** — and SHALL never touch a non-`codex/` worktree. Where the presence of work cannot be determined, it SHALL fail safe and keep.

#### Scenario: An empty `codex/` worktree is orphaned (e.g. by an external kill)
- **WHEN** an empty `codex/` worktree is orphaned (e.g. by an external kill)
- **THEN** `--gc` removes it

#### Scenario: A `codex/` worktree holds uncommitted work
- **WHEN** a `codex/` worktree holds uncommitted work
- **THEN** `--gc` keeps it and reports it — the salvage is not auto-destroyed

#### Scenario: A `codex/` worktree holds committed work not present on any non-co…
- **WHEN** a `codex/` worktree holds committed work not present on any non-codex branch
- **THEN** `--gc` keeps it — "no uncommitted changes" is not "no work"

#### Scenario: The work-check errors or is indeterminate
- **WHEN** the work-check errors or is indeterminate
- **THEN** `--gc` keeps the worktree rather than risk destroying salvage

#### Scenario: A non-`codex/` worktree exists
- **WHEN** a non-`codex/` worktree exists
- **THEN** `--gc` never touches it, and `--dry-run` removes nothing
