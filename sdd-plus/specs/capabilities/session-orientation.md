# Capability: session-orientation

Capability: session-orientation

## Purpose

`hooks/session_orient.py`, the `SessionStart` hook that orients the agent to Drydock project state and probes guardrail liveness. Read-only; ships with the plugin; fires in every session. It can only ever add context — never block, fail, or materially slow a session.

## Requirements

### Requirement: Silent outside a Drydock project
The hook SHALL emit nothing and exit 0 whenever the session is not inside a Drydock project. Project discovery SHALL be bounded (not an unbounded upward walk): the closest ancestor of `cwd` that has both an `sdd-plus/` directory and a Drydock marker (`AGENTS.md` or `sdd-plus/protocols/`), stopping at the git-repo root or `$HOME`, and excluding the plugin's own install tree and any `assets/project-scaffold` template. `cwd` is untrusted — if it is missing, empty, non-absolute, or not an existing directory, the hook SHALL no-op (never falling back to the process working directory).

#### Scenario: Non-Drydock directory is silent
- **WHEN** SessionStart fires with a `cwd` that has no Drydock project at or above it
- **THEN** the hook emits no output and exits 0

#### Scenario: Untrusted cwd is silent
- **WHEN** the SessionStart payload has a missing/empty/relative/nonexistent `cwd`
- **THEN** the hook emits no output and exits 0 (no process-cwd fallback)

#### Scenario: Real project is oriented
- **WHEN** SessionStart fires with `cwd` inside a Drydock project
- **THEN** the hook emits `additionalContext` describing PROJECT_CONTEXT state, active packets, and the guardrail verdict

### Requirement: Never blocks or fails a session
The hook SHALL always exit 0. Any internal error — including a `SystemExit` from any helper, a subprocess timeout, or malformed stdin — SHALL be caught and result in exit 0 with no emitted context. The guardrail probe SHALL run with a bounded per-probe timeout.

#### Scenario: Internal exception still exits 0
- **WHEN** the hook body raises any exception (including SystemExit)
- **THEN** it exits 0 and emits nothing

#### Scenario: Malformed stdin is safe
- **WHEN** stdin is empty or not valid JSON
- **THEN** the hook exits 0 and emits nothing

### Requirement: Emits only derived, non-sensitive signals
The emitted `additionalContext` SHALL contain only derived signals — enum states (missing/template/real), integer counts, boolean flags, and kebab-validated packet names — never raw file content, file excerpts, or absolute filesystem paths. Output SHALL be size-capped.

#### Scenario: No file content or absolute paths leak
- **WHEN** the project's files contain sensitive text or the project sits at a revealing absolute path
- **THEN** the emitted context contains no file excerpts and no absolute paths, only derived states/counts/names

### Requirement: Honest guardrail liveness probe
The hook SHALL report a guard as "live" only when running that guard script under the current interpreter emits a JSON `permissionDecision: deny` on stdout whose reason contains the guard's expected block fragment on a destructive probe payload, AND a benign control payload produces no deny — both exiting 0 (the guards deny via the JSON protocol, not exit 2). Any other outcome — including a guard that ALLOWS the destructive probe (fails open) — SHALL be reported as "degraded" (named) or "unverified". The verdict SHALL claim only what it verified (the guard SCRIPT denies under a probe), and a separate static check SHALL report whether `hooks.json` registers the guards. Because the guards deny with exit 0, the single-interpreter probe faithfully reflects the wrapped `python3 X || python X` chain (the `||` fallback never fires on a deny); the wrapped chain is separately regression-tested. The verdict SHALL be freshly measured each session (never cached).

#### Scenario: Live only on a genuine deny
- **WHEN** a guard emits a JSON deny with its expected reason on the destructive probe and no deny on the benign control
- **THEN** that guard is reported "live"

#### Scenario: A guard that fails open is not "live"
- **WHEN** a guard allows the destructive probe (emits no deny), or denies with the wrong reason, or denies the benign control
- **THEN** it is reported "degraded", never "live"

#### Scenario: Missing guard script is degraded
- **WHEN** a guard script is absent
- **THEN** it is reported "degraded (script missing)", never "live"

### Requirement: Session-state stamp for the completion gate
On SessionStart in a Drydock project, the hook SHALL best-effort write a per-session state file recording the current packet fingerprints as the session-start baseline, using the same shared discovery and fingerprint logic as the Stop-hook completion gate (so the two can never drift). The stamp SHALL be best-effort: any failure is swallowed and never affects orientation output, and the project tree SHALL remain read-only (the state file lives in a per-user directory). On `resume`/`compact` for a session whose state file already exists, the hook SHALL preserve the existing baseline and nudge ledger rather than resetting them (auto-compaction must not re-arm the nudge); only `startup`/`clear`, or the absence of a valid file, produces a fresh baseline.

#### Scenario: Startup stamps a fresh baseline
- **WHEN** SessionStart fires with source `startup` in a Drydock project
- **THEN** a state file with the current packet fingerprints and an empty nudge ledger is written

#### Scenario: Compact preserves the ledger
- **WHEN** SessionStart fires with source `compact` and a valid state file for the session already exists
- **THEN** the existing baseline and nudge ledger are preserved unchanged

#### Scenario: Stamp failure never affects orientation
- **WHEN** the state file cannot be written
- **THEN** orientation context is still emitted and the hook exits 0

### Requirement: OWNER_STATUS staleness sentinel
WHEN a Drydock project contains an OWNER_STATUS.md whose embedded project fingerprint no longer matches the freshly computed fingerprint, the orientation hook SHALL add a single line to its (already capped) additional context — phrased as a trust instruction to the agent ("do not cite it as current; if the Owner asks about status, run /drydock:brief in the Owner's language"), not as a prompt to volunteer a refresh — and SHALL emit it only when the session source is startup or clear, so resume and auto-compaction never re-arm it. The check SHALL be read-only toward the project tree, size-capped, and fail-silent: a missing, oversized, or unparseable OWNER_STATUS.md produces no sentinel line and no error. A matching fingerprint SHALL produce no line.

#### Scenario: Stale status file yields one trust instruction at true session start
- **WHEN** project state has changed since OWNER_STATUS.md was generated and the source is startup
- **THEN** orientation context includes one line telling the agent not to cite the file as current

#### Scenario: Resume and compaction do not re-arm the sentinel
- **WHEN** the session source is resume or compact
- **THEN** no sentinel line is emitted regardless of staleness

#### Scenario: Fresh or absent status file stays silent
- **WHEN** OWNER_STATUS.md matches current state or does not exist
- **THEN** no sentinel line is emitted

### Requirement: Probe marking and session coverage marker
The orientation hook SHALL set `DRYDOCK_PROBE=1` in the environment of every guardrail liveness probe child process, so probe denies are excluded from the event ledger while the probed verdict behavior remains byte-identical. Once per NEW session (source startup or clear — resume and compaction never re-count) it SHALL best-effort append a single `session` marker event to the per-user ledger (establishing machine coverage bounds for the Owner brief); this write targets the per-user state directory only — the project tree remains read-only — and every failure is silent.

#### Scenario: Probes prove blocking without polluting history
- **WHEN** orientation probes git-safety and secrets guards
- **THEN** both still report live via genuine blocks and the ledger gains no deny events

#### Scenario: Session coverage accrues silently
- **WHEN** a session starts in a Drydock project
- **THEN** one session marker is appended best-effort and orientation output is unchanged even if the append fails
