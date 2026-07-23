# Capability (delta): codex-conductor

Capability: codex-conductor

Extends the read-only conductor with an in-session entry point: the `/drydock:codex-review` command and its `review.py` CLI, so an Owner can delegate a code review to Codex and have Claude audit the findings.

## ADDED Requirements

### R7 — In-session review CLI with structured outcomes
`scripts/conductor/review.py` SHALL delegate a read-only review of one or more files to Codex and print a structured JSON result for EVERY outcome — never a bare traceback. It SHALL reuse the conductor primitives (discover / gauge / route / guard / delegate), refuse secret-bearing paths (checking given paths AND their realpaths), frame file content as untrusted data (prompt-injection defense), and enforce per-file and total byte caps.

- **WHEN** the review target is an ordinary file and Codex is available
- **THEN** the CLI prints `{ok: true, gauge, route, delegation.result}` with schema-conforming findings and exits 0

- **WHEN** a target path (or its realpath) is secret-bearing
- **THEN** the CLI prints `{ok: false, stage: "secret_guard"}` and does not send it

- **WHEN** Codex is not installed, a file is missing, a file exceeds the size cap, or a read fails
- **THEN** the CLI prints `{ok: false, stage: "discover"|"missing_file"|"too_large"|"read_error"}` — a structured outcome, not a traceback

### R8 — The command audits, never rubber-stamps
The `/drydock:codex-review` command SHALL treat Codex's findings as input to an independent audit — confirming, refuting, or refining each against the actual code and adding what wider context reveals — and SHALL present a synthesis to the Owner with Codex's remaining fuel noted. It SHALL never send secret-bearing files and SHALL not modify the repository.

- **WHEN** Codex returns findings
- **THEN** Claude verifies each (CONFIRM/REFUTE/REFINE) before presenting, and Codex's output is never treated as authoritative
