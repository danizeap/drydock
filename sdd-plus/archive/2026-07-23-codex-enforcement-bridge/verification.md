# Verification

## Change

codex-enforcement-bridge

## Automated Checks

- [x] `python -m pytest tests/test_codex_enforcement.py -q` → 15 passed. Covers: destructive git (str + argv-array), shell + PowerShell-native + apply_patch secret writes DENIED via the JSON protocol; benign command/write/apply_patch and secret *reads* silent; malformed input + unresolvable-plugin fail open (exit 0, no output); lowercase edit tool still denies (case-robustness regression); git pre-commit blocks a staged secret and allows a normal file.
- [x] `python -m pytest -q` (full suite) → 302+ passed, no regressions.
- [x] `python scripts/check_sync.py` → 11 pairs identical. The `.codex/` bridge and `hooks/git/pre-commit` are scaffold-only (no root twin), so intentionally outside the sync-pair set — confirmed not a gap.

## Manual Checks

- [x] Independent adversarial review by the `verifier` subagent. Verdict **VERIFIED WITH NOTES**; the two security-critical properties confirmed under an adversarial payload matrix: (a) **no fail-closed / session-brick path** — every dispatcher return is exit 0, including on malformed/non-dict/unresolvable inputs; (b) **real Codex attack surfaces denied** — destructive git (str/argv/`-C`), POSIX-redirect + PowerShell-native secret writes, and native `apply_patch` secret creations. Inline pre-commit `_FALLBACK` confirmed byte-equivalent to `protect_secrets._SECRET` (no drift).
- [x] Verifier notes resolved:
  - **Edit/Write case-sensitivity false-negative** — fixed: the edit branch now checks `path_is_secret` on the extracted path directly (case-robust), with a `write` (lowercase) regression test.
  - **Pre-commit fail-mode contract** — clarified: git-listing errors fail OPEN (never brick committing); secret-detection failure fails CLOSED (block), now explicit in code + docstring.
  - **apply_patch-via-shell timing gap** — documented plainly in the delta spec "Known limitations (v1)": a patch smuggled through a shell command is caught by the git hook at commit time, not write time.
  - **Fail-open when the plugin is unresolvable** — documented as an accepted v1 limitation (git hook is the backstop).

## Documentation Updates

- [x] Specs updated: delta spec `specs/codex-enforcement-bridge.md` (R1–R5 + Known limitations).
- [x] Setup updated: `commands/init-project.md` step 5 — copy `.codex/`, offer the git-hook install with an Owner-approval gate on `.git/hooks/`.
- [ ] README/operator-guide: deferred to the release commit (the "cross-tool enforcement" upgrade note lands with the CHANGELOG at ship time).
- [ ] No documentation update needed. Reason:

## Result

VERIFIED. The stateless critical floor (secrets + destructive git) now enforces under Codex via the `.codex/` dispatcher (JSON deny, fail-open) with an agent-agnostic git pre-commit backstop; all verifier notes resolved. Ready for `/drydock:sync` then archive.

Note for release: the working tree also contains the separate, already-archived **conductor-mvp** change (`scripts/conductor/`, `tests/test_codex_bridge.py`, `tests/fake_codex.py`, `docs/AI_OPERATOR_GUIDE.md`, `sdd-plus/specs/capabilities/codex-conductor.md`). Keep the two as distinct commits when shipping.
