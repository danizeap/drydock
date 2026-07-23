# Capability (delta): codex-conductor

Capability: codex-conductor

Hardens the mutating-delegation gate against false confidence, and fixes handoff/review reporting defects found in the first real-world field report.

## MODIFIED Requirements

### R10 (modified) — The gate must never report green on a result it cannot trust
In addition to applicability-first behaviour, the gate SHALL distinguish "could not verify" from "tests failed", and SHALL decide trust by an **ALLOW-LIST**: a test command is trusted only when it is a SIMPLE command, optionally `&&`-chained (the one chain that short-circuits, so a failure propagates). Any other construct — a pipe, `;` or bare `&` sequencing, `||`, a newline, a backtick or `$( )` subshell — makes the exit code untrustworthy, and an **unrecognised construct SHALL default to untrusted**. `2>&1` is a redirect, not a separator, and remains trusted. Quoting SHALL be platform-aware (`'` quotes only on POSIX; cmd.exe does not). The trust signal SHALL default to **false** when absent (fail-closed). A broken environment (worktree with `package.json` but no `node_modules`) SHALL likewise be `unverifiable`. In every untrusted case the verdict SHALL be **`unverifiable`** with `clears: false` — never `green` — and the reason SHALL name the actual cause. Honest passes SHALL still be `green` and honest failures `red`.

**Declared limit (disclosure, not a defect):** the gate judges the top-level command's SHAPE only. If that command delegates to a script runner (`npm run ci`, `make test`, `bash -c "…"`), masking *inside* that script is invisible — `bash -c "false; true"` is genuinely a simple command that exits 0. This SHALL be disclosed as an advisory at point of use, not silently trusted.

- **WHEN** the test command contains a pipe, `;`, bare `&`, `||`, a newline, or a subshell and exits 0
- **THEN** the verdict is `unverifiable` with `clears: false` (not `green`)

- **WHEN** the trust signal is absent from the test result
- **THEN** it is treated as untrusted (fail-closed) and the verdict is `unverifiable`

- **WHEN** the worktree has `package.json` but no `node_modules` and the command exits 0
- **THEN** the verdict is `unverifiable` with `clears: false`

- **WHEN** a simple or `&&`-chained command passes (or fails) in a sound environment
- **THEN** the verdict is `green` (or `red`) as before — the gate must stay usable

- **WHEN** the command delegates to a script runner whose internals we cannot inspect
- **THEN** an advisory discloses that limit; the verdict is unchanged (advisories never gate)

## ADDED Requirements

### R23 — Coverage-gap advisory
The gate SHALL emit an `advisories` list, including a note when the diff changes code but contains no test file. This is ADVISORY only — it SHALL NOT change `clears`.

- **WHEN** the diff adds/changes code with no test file present
- **THEN** an advisory names the coverage gap while the verdict is decided solely by the test result

### R24 — Handoff distinguishes all packets from in-flight; result names the path
`gather_state()` SHALL report `packets` (all un-archived) and `in_flight_packets` (unchecked tasks or an unfilled verification), and the rendered handoff SHALL lead with in-flight. The `write` result SHALL include a `path` field.

- **WHEN** a finished packet sits un-archived in `sdd-plus/changes`
- **THEN** it appears in `packets` but NOT in `in_flight_packets`

### R25 — Review findings identify their file
Each review finding SHALL carry the `file` it refers to, so multi-file reviews can be triaged.

- **WHEN** several files are reviewed in one run
- **THEN** every finding names its file
