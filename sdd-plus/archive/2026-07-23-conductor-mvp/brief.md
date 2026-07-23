# Brief

## Change

conductor-mvp — the first real multi-agent capability: Drydock can delegate a **read-only** analysis/review task to Codex, fuel-aware, and get schema-locked structured output back to audit. Productionizes the scratch prototype proven live on 2026-07-23 (see `sdd-plus/specs/multi-agent-orchestration-vision.md` §8).

Intake: Mode **FULL** (privileged external integration). Primary skill: `backend`; supporting: `mcp-ranger` (Codex is a privileged actor), `testing`. Approvals: Owner directed the build; the empirical validation (§8) de-risks feasibility. **Stop conditions:** any code path that lets the conductor **mutate the repo** or run Codex non-read-only (that is the enforcement-bridge's job, out of scope here); any path that ships secrets/`.env`/credentials to Codex; any test that spends Codex quota in CI; any hardcoded Codex binary path.

## What this means for your product

Drydock gains a real teammate. It can hand Codex a bounded, **read-only** job — "review this", "analyze that", "find risks here" — pick the right Codex model based on how much Codex fuel is left, and get back a structured result that Claude then independently audits. Two systems making the work better, safely, with no ability (yet) to change your files.

## User Need

The prototype proved the loop works (discover core → read fuel gauge → route → delegate with `--output-schema` → audit). But a prototype in scratch is not a capability: it must become a tested, governed module with safe failure modes, no hardcoded stale binary, controlled cost, and a hard read-only boundary. Mutating delegation waits for `codex-enforcement-bridge` (so Codex writes are guarded); this packet ships the safe half now.

## Problem

1. No reusable module — the logic lives in throwaway scratch files.
2. Discovery must never hardcode the core path (the install hash dir changes every update) and must never fall back to the stale `.sandbox-bin` binary (can't run flagship).
3. Failure must be **safe and legible** — no tracebacks, no leaked app-server processes, no silent exit-0-on-failure, clear diagnostics.
4. **Data-governance:** delegation ships content to an external model (OpenAI). The conductor must refuse to send secret-bearing content (`.env`, keys, credentials) — reuse the plugin's secret-path awareness.
5. Cost: every delegation carries a context tax (~170K vs ~16K) governed by the working root — the module must default to a lean `-C`.
6. Tests must prove all of the above **without spending Codex quota** (fake the Codex subprocess).

## Scope

In scope:

1. **`conductor/codex_bridge.py`** (location TBD) — `discover_core()` (glob newest, never sandbox), `read_rate_limits()` (hardened app-server reader from §8, already review-audited), `delegate(prompt, schema_path, model, cwd)` → `{exit, usage, result, stderr_tail}`, all read-only (`-s read-only`, `--ephemeral`, lean cwd).
2. **Routing helper** — fuel-aware model selection (documented policy, not a black box): heavy + fuel>floor → flagship; else workhorse; light → workhorse.
3. **Secret-guard on outbound content** — refuse to delegate content whose source path is secret-bearing; reuse `path_is_secret`.
4. **Tests** (no live quota) — discovery picks newest & rejects sandbox; gauge parse incl. failure modes (spawn error, early server exit, timeout, non-dict line) via a fake `codex` script/subprocess monkeypatch; delegate result parsing; secret-guard refusal. Plus an **opt-in** live smoke test (documented, not in CI).
5. **Docs** — operator guide: "Codex as a read-only teammate" + the discover/gauge/delegate contract.
6. **Delta spec** — new capability `codex-conductor` (read-only delegation + fuel gauge + safe-failure contract).

Out of scope (later bricks): mutating delegation (needs `codex-enforcement-bridge`); Claude-side usage ledger / dual-tank endurance routing; HANDOFF relay; parallel divide-and-conquer; adversarial-security mode.

## Acceptance Criteria

- [ ] `discover_core()` returns the newest `%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe`, never the stale sandbox copy; missing → structured fail (not an exception).
- [ ] `read_rate_limits()` always returns `{ok:true,result}` or `{ok:false,stage,error,stderr}` — never a traceback; the app-server process is always reaped (no leak across repeated calls).
- [ ] `delegate()` runs **read-only** against a lean cwd, returns schema-conforming `result` + `usage`, and has **no code path that writes into the repo**.
- [ ] Content from a secret-bearing path is **refused** before it leaves the machine.
- [ ] Full test suite passes **without spending Codex quota** (Codex subprocess faked); the live smoke test is opt-in and documented.
- [ ] Verifier confirms: read-only boundary intact, no hardcoded/stale binary, failures safe, no secret egress, no quota in CI.

## Impact Areas

- Backend: new conductor module + routing + tests.
- Frontend: none.
- Data model: none.
- API: internal module contract (discover / gauge / delegate).
- AI/model behavior: introduces external-model delegation (Codex) — read-only, fuel-aware.
- Documentation: operator guide + the vision note cross-link.
- Operations/security: first external-agent integration — `mcp-ranger` lens (privileged actor, read-only + no secret egress). Outbound-data-flow governance.

## Open Questions

- Module home: `scripts/conductor/` vs a top-level `conductor/` package? (Lean toward `scripts/` alongside `sdd.py`.)
- Test fake: a tiny fake-`codex` script the tests invoke, vs monkeypatching `subprocess`? (Fake script is more honest — exercises real arg handling.)
