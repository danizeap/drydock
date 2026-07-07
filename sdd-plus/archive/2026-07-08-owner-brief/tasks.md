# Tasks

## Change

owner-brief

## Implementation

- [x] Red-team the design (3 adversaries: lying-brief/false-peace, ledger robustness+privacy+latency, adoption/nag) and fold findings into this plan (22 attacks, all mitigations adopted — see plan "Red-team response").
- [x] `append_event()` + `read_events()` + frozen category allowlist in `hooks/_drydock_common.py` (no fsync, O_APPEND single-write lines, date-only ts, lstat/tail-window/per-line-cap reader, probe env no-op, ledger-created marker), with tests (rotation, torn lines, symlink, non-UTF8, allowlist coercion, probe exclusion, verdict-delivery independence primitive).
- [x] Wire the four writers (packet_guard deny/warn, protect_secrets deny, git_safety deny, completion_gate nudge) as the last statement post-verdict, each individually wrapped; verdict-delivery byte-identical test per writer; allow-path zero-I/O preserved (latency test).
- [x] session_orient: `DRYDOCK_PROBE=1` in probe child env; one `session` ledger marker per startup; staleness sentinel as a trust instruction gated on source in (startup, clear); tests.
- [x] packet_guard: always-deny class for basename `owner_status.md` (Write/Edit/MultiEdit + Bash write targets, fires with or without an active packet, fixed recovery message naming /drydock:brief); tests incl. fixture suppression and the sanctioned-path note.
- [x] Build `scripts/brief.py`: plugin-anchored import shim; own rung assigner (ascent-requires-positive-evidence, closed PASS grammar, override/incomplete-archive demotion); FACTS block with provenance classes, goal field (one-sentence truncation), coverage bounds, not-initialized state, unavailable-not-zero everywhere; `--write-status` (frozen en/es label sets, visible staleness first line, HEAD short-sha, fingerprint+lang comment, no-change short-circuit, atomic write); `--record-verify <name>` (re-runs the deterministic gate, appends verify-run with packet hash only on genuine pass). Golden tests: every rung, every degenerate tree (no tasks.md, prose tasks, headingless verification, NOT VERIFIED result, forced archive, hand-moved archive, decoy module, young ledger + old archives, not-initialized, both langs).
- [x] Add `commands/brief.md` (chat rendering translate-only + never unprompted + authority line + first-write git choice), wire `commands/verify.md` (--record-verify after gate pass), `commands/new.md` (two-slot Owner-line form), `commands/archive.md` (closing regenerate-when-exists), `commands/status.md` (authority line).
- [x] CI smoke for brief.py; docs (operator guide inventory + brief section + state-dir diagnostic, README Owner-surface paragraph).
- [x] Update delta specs to pin the red-team scenarios (owner-brief rung grammar/write-guard/coverage; session-orientation sentinel+probe+marker; packet-guard owner_status deny) — before implementing the specced behavior.
- [x] Run verification: full suite, check_sync, live brief render + --write-status on this repo, verifier subagent (two rounds: NOT VERIFIED → fixes → VERIFIED WITH NOTES; falsification-proven).
