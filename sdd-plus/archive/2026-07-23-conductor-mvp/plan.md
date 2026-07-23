# Plan

## Change

conductor-mvp

## Approach

1. **`scripts/conductor/codex_bridge.py`** (new package `scripts/conductor/`):
   - `discover_core()` — glob `%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe`, return newest by mtime; never the `.sandbox-bin` copy; `None` if absent.
   - `read_rate_limits(core, timeout_s=25)` — the hardened app-server JSON-RPC reader (already Codex-reviewed + conductor-audited in vision §8): structured `{ok,...}` results, early-exit/EOF detection, monotonic deadlines, guaranteed process reap.
   - `delegate(prompt, schema_path, model, cwd, timeout_s=240)` — runs `codex exec` with **hardcoded** safety flags `-s read-only --ephemeral --skip-git-repo-check --output-schema <s> --output-last-message <f> -C <lean cwd>`; parses `usage` from JSONL + the schema-locked result file; returns `{exit, usage, result, stderr_tail}`. **No parameter can inject write/sandbox-escalation flags.**
   - `route(task_weight, gauge)` — documented fuel-aware model policy.
   - `guard_outbound(paths)` — refuse delegation whose source path is secret-bearing, reusing `hooks/_drydock_common.path_is_secret`.
2. **Tests** — `tests/fake_codex.py` (a stand-in that speaks the app-server handshake + emits schema-conforming `exec` output, zero network/quota) invoked through the *real* subprocess path; `tests/test_codex_bridge.py` covers discovery (newest / reject-sandbox / none→fail), gauge (ok + spawn-error/early-exit/timeout/non-dict-line), delegate (result+usage parse, **argv asserts `-s read-only` and no `--dangerously*`/`workspace-write`**), secret refusal, route policy.
3. **Docs** — operator-guide section "Codex as a read-only teammate"; cross-link vision §8.
4. **Delta spec** — `specs/codex-conductor.md`.

## Files Expected To Change

- NEW `scripts/conductor/__init__.py`, `scripts/conductor/codex_bridge.py`
- NEW `tests/fake_codex.py`, `tests/test_codex_bridge.py`
- `docs/AI_OPERATOR_GUIDE.md` (+ README pointer)
- NEW `sdd-plus/changes/conductor-mvp/specs/codex-conductor.md`
- `CHANGELOG.md` (at release)

## Risks

- **Read-only boundary escape** — a caller-injected flag re-enabling writes. Mitigation: `delegate()` builds argv from a fixed safety prefix; caller supplies only prompt/schema/model/cwd; a test asserts the emitted argv. Sandbox is always `read-only`.
- **Secret egress to OpenAI** — delegating secret-bearing content. Mitigation: `guard_outbound` blocks path-based secrets; free-form prompt content remains the (governed) caller's responsibility — documented, not silently assumed safe.
- **Process leak / hang** — inherited-safe from the hardened reader (reap in `finally`, timeouts).
- **Quota spent in CI** — tests must never touch real Codex. Mitigation: fake-codex; the live smoke test is opt-in behind an env flag, excluded from CI.
- **Layout drift** — if OpenAI changes the `bin` layout, discovery returns `None` → structured fail, never a crash.

## Rollback

All new files + additive docs. `git revert` is clean. No change to existing hooks, gates, or lifecycle. The capability is inert unless explicitly invoked.
