# Capability (delta): codex-enforcement-bridge

Capability: codex-enforcement-bridge

Makes the cost of a mutating delegation visible, lets the Owner scope it without hard-bounding it, and says plainly when the deterministic gate is weak evidence.

## ADDED Requirements

### R1 — Every mutating run reports what it cost
`mutate()` SHALL report the cost of the delegation: Codex-reported token counts where available, and the **fuel-gauge delta across the run as the authoritative figure**. Any quantity that cannot be measured SHALL be reported as `null` — never as zero, and never estimated.

- **WHEN** Codex reports usage and both gauge reads succeed
- **THEN** the result carries token counts and `fuel_used_percent`, the difference between the before and after readings

- **WHEN** usage is absent, malformed, or a gauge read fails
- **THEN** the affected fields are `null` — a cost report that invents a number would have the Owner budget against a fiction

- **WHEN** the quota window resets mid-run, so the after-reading is lower than the before-reading
- **THEN** `fuel_used_percent` is `null` rather than a negative or wrapped value

### R2 — File scoping is opt-in and SOFT
`--files` SHALL be optional; omitting it SHALL leave delegation behavior unchanged. When given, the named targets' current content SHALL be inlined into the task so Codex need not search for them, and Codex SHALL remain free to edit files outside that set. Edits outside the declared scope SHALL be **disclosed**, never silently permitted and never blocked.

- **WHEN** `--files` is omitted
- **THEN** the prompt is the operator's task verbatim and no scope is reported

- **WHEN** files are named
- **THEN** their content is inlined behind a boundary marker no content or path can close, and the prompt states that coupled files may still be edited

- **WHEN** Codex edits a file outside the declared set
- **THEN** the result lists it in `scope.out_of_scope` and an advisory names it — the change is not blocked, because the coupled files an operator forgets to name are exactly the ones that make a change complete

- **WHEN** a declared file is never touched
- **THEN** it is reported in `scope.declared_untouched`

### R3 — Naming a file for inlining cannot leak a secret
A file named for inlining has its content sent off-machine, so it SHALL receive the same treatment an explicitly named review path receives: the name guard SHALL be applied to the **resolved** path as well as the given one, the path SHALL resolve **inside the worktree**, and a target that is secret-bearing **by name** or whose **content** matches high-confidence secret material SHALL cause the run to be refused **before Codex is spawned**. Size SHALL be taken from the same handle the content is read from, and both the per-file size, the total size, and the **number of names** SHALL be capped.

- **WHEN** a named target is secret-bearing by name or by content
- **THEN** the run is refused (`stage: scope_guard`) and no delegation process is started

- **WHEN** a named target reaches a secret file through a **symlink** under an innocent name
- **THEN** the resolved path is guarded too, so the alias is refused

- **WHEN** the alias is a **hardlink**
- **THEN** it is NOT caught — a hardlink has no target, so no path-resolution guard can see through it. This is a **stated limit**, shared with `review.py`, not a covered case

- **WHEN** a named target resolves outside the worktree (e.g. `../../secrets.txt`) or is an absolute path
- **THEN** the run is refused — `--files` takes repo-relative paths and cannot be used to read arbitrary files

- **WHEN** the named targets exceed the per-file cap, the total inline budget, or the maximum number of names
- **THEN** the run is refused with guidance to name fewer files or omit `--files`

- **WHEN** a file grows between the size check and the read
- **THEN** the read is hard-capped and the run is refused rather than inlining past the limit

- **WHEN** a named target does not exist yet
- **THEN** it is still passed as in-scope — it may be the file to create

### R4 — Say when the deterministic gate is weak evidence
The result SHALL describe the diff's **shape** — file count and a **measured** cross-file repetition of added-line structure — and SHALL raise a non-gating advisory when a diff is both wide and divergent, because a passing test suite is weakest exactly there. Repetition SHALL be reported as `null` when it could not be measured, and a shape SHALL NOT be reported as repetitive on the basis of an absent measurement. **No text a delegate can write into a changed file SHALL alter which file the surrounding lines are attributed to** — the party under review cannot suppress or redirect its own advisory. The advisory SHALL NOT change the gate verdict; thresholds and the number of files actually compared SHALL be reported alongside the measurement.

- **WHEN** many files change with structurally similar additions (a mechanical sweep)
- **THEN** `repetition` is a measured value at or above the stated threshold, `compared_files` is at least 2, the shape is `wide-repetitive`, and no advisory is raised

- **WHEN** many files change with structurally dissimilar additions
- **THEN** `repetition` is a measured value below the threshold, the shape is `wide-divergent`, and an advisory states that the diff is a set of separate judgment calls needing a real read

- **WHEN** repetition cannot be measured (deletion-only, binary, or unparseable diff)
- **THEN** `repetition` is `null`, the shape is `unknown` rather than `wide-repetitive`, and an advisory states the signal is unavailable — an absence of evidence SHALL NOT read as reassurance

- **WHEN** an added line's own text resembles a diff header (e.g. `++ b/x.py`), with further changed lines following it in the same file
- **THEN** it is consumed as file content, no phantom file appears, and **every** changed file is still attributed its own lines (`compared_files` is unchanged) — the reviewed party cannot suppress or redirect its own advisory

- **WHEN** the comparison is bounded for cost
- **THEN** the result says so (`sampled`, `compared_files`) rather than presenting a partial measurement as complete

- **WHEN** any diff-shape advisory is raised
- **THEN** `verdict` and `clears` are exactly what they would have been without it
