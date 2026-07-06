# Plan

## Change

autopilot-floor

## Approach

Test-first, safety-critical order (the hook must never harm a session):

1. **Delta specs** — `session-orientation` (new capability) and an ADDED requirement on the existing `change-packet-gates` capability (governed override). Scenarios double as the test plan.
2. **Red-team the hook design first** — independent adversaries hunt three failure classes before code exists: (a) pollutes/interferes with a non-Drydock session, (b) blocks/hangs a session, (c) reports "live" when a guard is actually inert. Findings become defended-against scenarios.
3. **Governed `--force` in `sdd.py`** — add `--reason`; when `--force` is used, require `--reason` (else exit non-zero with guidance) and append `| <date> | OVERRIDE | waived: <gates> | <reason> |` to the change's `decision-log.md`. Pure CLI change, testable in isolation. Sync scaffold copy.
4. **`session_orient.py`** — structure so **every path exits 0**:
   - Wrap the whole body in `try/except`; on any exception, print nothing and `return 0`.
   - Read stdin JSON; get `cwd`. Locate `sdd-plus/` from cwd/ancestors; if none → print nothing, exit 0 (the no-op rule; first test).
   - Read-only scan via pure helpers imported from the plugin's `scripts/sdd.py` (`task_counts`, `delta_spec_files`, placeholder checks) — never mutate.
   - Compose a compact human-readable status string.
5. **Guardrail liveness self-test** — invoke `git_safety.py` (payload `git reset --hard`) and `protect_secrets.py` (Write `.env`) as subprocesses with a short timeout; a guard is "live" **only if it exits exactly 2**. Any other outcome (0, crash, timeout, missing) → "degraded", naming which guard. The verdict wording states exactly what was tested and claims nothing more.
6. **Emit** `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<status>"}}` on stdout, exit 0.
7. **Wire** `hooks.json` (SessionStart, matchers startup+resume, python3||python). Tests, CI smoke, docs (operator guide §1/§10, DEVELOPING, CHANGELOG).
8. Run suite + check_sync; verifier subagent (adversarial false-"live" check); sync delta specs; archive.

## Files Expected To Change

- hooks/session_orient.py (new)
- hooks/hooks.json
- scripts/sdd.py + assets/project-scaffold/scripts/sdd.py
- tests/test_session_orient.py (new), tests/test_sdd_gates.py (governed force)
- .github/workflows/ci.yml (orient smoke test)
- docs/AI_OPERATOR_GUIDE.md, docs/DEVELOPING.md, CHANGELOG.md
- this packet + 2 delta specs

## Risks

- **[HIGH] Polluting non-Drydock sessions.** Plugin hooks fire everywhere. Mitigation: no-op rule (no `sdd-plus/` → empty output), first test case.
- **[HIGH] Blocking/hanging a session.** Mitigation: total try/except → exit 0; short subprocess timeout on the self-test; a test induces an exception and asserts exit 0.
- **[MEDIUM] False "live".** Mitigation: "live" requires exit *exactly* 2 from *both* guards; a test points the self-test at a broken guard copy and asserts "degraded"; verifier adversarially confirms no false-live path.
- **[MEDIUM] Latency.** Mitigation: file reads + 2 tiny subprocess checks, short timeout; consider self-test on `startup` only.
- **[LOW] Plugin-vs-project sdd.py version skew** for imported helpers. Mitigation: only stable read-only functions.
- **[LOW] Governed `--force` breaks muscle memory.** Mitigation: helpful message + CHANGELOG (today's archives used no `--force`).

## Rollback

All tracked text; `git revert` restores prior behavior. The SessionStart hook can be disabled instantly by removing its `hooks.json` entry (Owner action) with zero effect on the rest of the plugin. `session_orient.py` performs no writes; governed `--force` only *adds* a requirement and an append-only record.
