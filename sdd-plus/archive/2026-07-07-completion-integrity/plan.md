# Plan

## Change

completion-integrity

## Approach

1. **Red-team first** (running): three adversaries on loop/nag, breakage/blind-spots, and the state-file surface. Every high/medium finding becomes a coded defense + a pinned test + a delta-spec scenario.
2. **Delta specs**: `completion-gate` (new capability) and `session-orientation` (MODIFIED — adds the session-state stamp duty). This is the repo's first MODIFIED delta; sync must preserve all unmentioned session-orientation requirements.
3. **Session-state stamp in `session_orient.py`**: after composing context (never before — orientation must not depend on the stamp succeeding), write `{schema:1, session_id, started_at, nudged:false, fingerprints:{packet: {pending, verification_pending, latest_mtime}}}` to `tempfile.gettempdir()/drydock-state-<sanitized-session-id>.json`. Sanitize session_id to `[A-Za-z0-9_-]{1,64}`. Write failures are swallowed (stamp is best-effort; the gate fails silent without it).
4. **`hooks/completion_gate.py`**: read stdin JSON → sanitize session_id → bounded Drydock discovery (same rules as orient: marker required, git-root/HOME stop, plugin-tree/scaffold excluded, untrusted cwd) → load state file (missing/corrupt/oversized → silent) → honor `nudged:true` and any `stop_hook_active` field defensively → recompute fingerprints → if a Pending-verification packet's fingerprint differs from start AND not yet nudged: set `nudged:true` FIRST (write before speaking — if the write fails, stay silent: never risk a loop), then emit `{"decision":"block","reason":...}` → else silent. Whole body `except BaseException` → exit 0.
5. **Wire hooks.json** Stop entry; tests; CI smoke (gate always exits 0 on malformed inputs); docs.
6. Suite + check_sync; adversarial verifier (mandate: force a loop / a false nudge — must fail); sync deltas (first MODIFIED merge, done carefully by hand per spec-sync semantics); archive.

## Files Expected To Change

- hooks/completion_gate.py (new), hooks/session_orient.py, hooks/hooks.json
- tests/test_completion_gate.py (new), tests/test_session_orient.py (stamp tests)
- .github/workflows/ci.yml, docs/AI_OPERATOR_GUIDE.md, CHANGELOG.md
- this packet + 2 delta specs

## Risks

- **[HIGH] Nudge loop** if the nudged flag can't persist. Defense: write-the-flag-before-speaking; any write failure → silent-allow.
- **[HIGH] Nagging legitimate sessions.** Defense: three ANDed conditions (Pending verification ∧ fingerprint changed this session ∧ not yet nudged); pure conversation never matches; red-team pressure-tests the detector.
- **[MEDIUM] State-file surface** (traversal, symlink, tamper, collision). Defense: strict session_id sanitization, size caps, schema check, silent-allow on any anomaly; a tampered file can at worst suppress one nudge or cause one extra nudge — never block permanently (nudged is set before speaking).
- **[MEDIUM] mtime granularity/semantics** (git checkout touches mtimes; FAT 2s granularity). Defense: fingerprint combines counts + flags + mtime, and the gate additionally requires verification_pending now; acceptable residual: a rare extra single nudge, capped at one per session.
- **[LOW] Per-turn cost**: the gate runs on every Stop — pure file reads, no subprocesses; budget trivial.

## Rollback

Tracked text only; `git revert`. The Stop hook can be disabled instantly by removing its hooks.json entry; removing the stamp from session_orient returns it exactly to v0.2.0 behavior. State files are transient temp files, ignorable.
