# Capability (delta): codex-conductor

Capability: codex-conductor

Adds auto-discovered review (`--diff`) so cross-model review is a natural pre-`verify` step, with the stronger guards that auto-discovery demands.

## ADDED Requirements

### R26 — Review what changed, discovered honestly
`review.py --diff [--base <ref>]` SHALL review the CURRENT CONTENT of files changed in the working tree (vs HEAD, including untracked) or vs an explicit base, and SHALL report deleted paths separately. Path listing SHALL be NUL-delimited (git C-quotes unusual paths). A git failure SHALL be reported as an error — **never** as an empty change set.

- **WHEN** files are modified and new files are untracked
- **THEN** both appear in the reviewed set, while binaries/generated files (`.png`, `.lock`, `.min.js`, …) are excluded

- **WHEN** a tracked file's TYPE changes (e.g. a regular file replaced by a symlink) or a file is unmerged
- **THEN** it appears in the changed set — a status filter SHALL NOT drop it into "no changes"

- **WHEN** files were deleted in the change
- **THEN** their paths are reported to the Owner, and named to the reviewer **except where R27 withholds them** — a secret-bearing deleted path is disclosed to the Owner and never sent

- **WHEN** the git query fails (e.g. an invalid `--base`)
- **THEN** the result is `stage: git_error` — not "no changes"

### R27 — Auto-discovery never widens what leaves the machine
For an auto-discovered set the tool SHALL skip-and-disclose (never send) any path that is secret-bearing **by name**, whose **content** matches high-confidence secret material, or whose realpath resolves **outside the repository**. An **explicitly named** secret path (by name or content) SHALL be refused outright. Where containment **cannot be established**, the tool SHALL fail closed. No skip SHALL be silent — **every** outcome, success or failure, SHALL carry the skip lists.

- **WHEN** a changed file is secret-bearing by name or contains secret material
- **THEN** it is skipped, listed in `skipped_secret`, and never sent

- **WHEN** a changed path is a symlink resolving outside the repository
- **THEN** it is skipped and listed in `skipped_outside_repo`

- **WHEN** the operator explicitly names a secret-bearing path
- **THEN** the run is refused (`secret_guard` / `secret_content`) rather than silently skipped

- **WHEN** the repository root cannot be determined during auto-discovery
- **THEN** the run is refused (`stage: no_repo_root`) — containment is unverifiable, so nothing is sent

- **WHEN** the run ends in an error stage (`too_large`, `read_error`, …) after files were skipped
- **THEN** the skip lists are still present in the result — an early failure is still an outcome

- **WHEN** every candidate is filtered out
- **THEN** the result is `stage: nothing_to_review` with the skip lists populated

### R28 — Nothing reviewed can escape its delimiter
The prompt SHALL delimit every untrusted region with a boundary marker absent from **all** interpolated text — file content **and** file paths (escalated until unique) — so neither a file nor a *file name* can close its own fence and reach the instruction region. Deleted paths are untrusted data and SHALL be delimited, not placed in the instruction region. Any git ref accepted from the operator SHALL be validated before it reaches a git argv. Every outcome, including argument errors, SHALL be structured JSON.

- **WHEN** a reviewed file's content or its **path** contains the boundary marker text
- **THEN** the marker escalates so neither can close it

- **WHEN** a change deletes a file whose name reads as an instruction
- **THEN** the name appears inside a delimited data region, never in the preamble

- **WHEN** `--base` is option-shaped (e.g. `--output=<path>`)
- **THEN** it is rejected before git runs, so it cannot make git write a file

- **WHEN** the CLI is invoked with invalid arguments
- **THEN** it emits `stage: bad_arguments` as JSON rather than bare usage text, and writes **nothing** to stderr — a caller merging the streams still receives valid JSON

- **WHEN** flags are combined such that operator-specified scope would be ignored (`--diff` with paths, `--base` without `--diff`)
- **THEN** the run is refused as `bad_arguments` rather than silently discarding the scope
