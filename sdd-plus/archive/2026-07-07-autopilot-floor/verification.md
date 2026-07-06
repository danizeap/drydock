# Verification

## Change

autopilot-floor

## Automated Checks

- [x] `python -m pytest tests/ -q` → **147 passed** (129 prior + 18 new in test_session_orient.py; governed-force tests already counted). New tests cover every red-teamed invariant: silent-outside-Drydock + bounded discovery (INV1: plugin-tree/scaffold exclusion, marker required, git-root stop, foreign-ancestor), always-exit-0 incl. SystemExit (INV2), false-"live" refusal (INV3: exit-2-wrong-reason, blocks-benign, missing-script), and no content/abs-path leak (INV4).
- [x] `python scripts/check_sync.py` → **OK, 10 pairs identical** (session_orient.py, hooks.json, tests, CI are plugin-level / dev-only, not scaffolded; only the sdd.py governed-force change is dual-copied and was synced).
- [x] `python scripts/release.py --check` → **OK at 0.1.6** (version lockstep unaffected).
- [x] Live hook smoke: non-Drydock cwd → empty/exit 0; dev repo → `additionalContext` with PROJECT_CONTEXT/packet/guardrail state and `git-safety live; secrets live; wiring: registered`; malformed/empty/missing-cwd → empty/exit 0.
- [x] CI orient smoke (run locally): malformed, empty, and missing-cwd payloads all exit 0.
- [x] `ast.parse` on session_orient.py and sdd.py → OK.

## Manual Checks

- [x] Ran a 4-adversary red-team of the hook design BEFORE implementation; the top finding (reusing sdd.py's unbounded `find_root` → orienting on a foreign repo) and all other high/medium findings are defended in code and pinned by tests.
- [x] Confirmed the probe uses `sys.executable` with `shell=False` + an argv list (no `python3||python` shell that could hang on a Windows Store stub), and the guard paths come from `Path(__file__).parent` (not env/cwd).
- [x] Confirmed the emitted context carries only enum states, counts, and kebab-validated names — no file content, no absolute paths — and is size-capped.
- [x] Governed `--force`: bare `--force` refused; override recorded to decision-log.md (unit-tested).

## Documentation Updates

- [x] Operator guide updated (3-hook inventory incl. session_orient; governed-force in §4.5/§4.6).
- [x] CHANGELOG `## 0.2.0 — autopilot floor` drafted.
- [x] Specs updated: delta specs session-orientation.md + change-packet-gates.md (to be synced at archive).
- [x] No README change needed. Reason: user-facing surface is agent-side context injection; the operator guide + CHANGELOG cover it.

## Independent Verification

- [x] `drydock:verifier` subagent review (FULL-mode gate) → **VERIFIED** (2026-07-07). Independently re-ran pytest (147), check_sync (10/10), release --check; mapped all 5 delta requirements to code + asserting tests (file:line); drove the governed override end-to-end through the real CLI (refusal, recorded override traveling to archive, no-record-when-clean). **Adversarial mandate held on every axis:** hanging/wrong-reason/block-everything/crashing/missing guards all yielded degraded/unverified — never a false "live"; malformed stdin, SystemExit, hanging guards, and a 200-packet repo could not make the hook exit non-zero or hang (probes bounded ~2s, output capped); scaffold/plugin-tree/foreign-git-repo cwds all stayed silent; no file content or absolute path in the emitted context.

## Result

**PASS.** Implementation complete and independently verified: 147 tests green, check_sync green, version lockstep intact; the hook is proven silent-outside-Drydock, always-exit-0, honest in its liveness verdict, and leak-free — built against a pre-implementation red-team and confirmed by an adversarial verifier. Remaining (Owner-gated): the v0.2.0 cut via `release.py 0.2.0` and publish.
