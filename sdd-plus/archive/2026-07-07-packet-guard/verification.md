# Verification

## Change

packet-guard

## Automated Checks

- [x] `python -m pytest tests/ -q` → **188 passed** (165 prior + 23 new in test_packet_guard.py). New tests pin: silence for non-Drydock/out-of-project/packet-active/exempt paths; the sibling-prefix containment case; non-kebab packets counting as active; bare decoys NOT counting; the deny matrix (migrations, db/migrate, case-insensitive, Dockerfile/compose) with soft-segment suppression (tests/, fixtures/, examples/); auth demoted to warn; new-vs-existing workflow split; Bash redirect deny + Bash no-warn; warn-once + persist-failure silence; the cross-hook warned-preservation test; garbage-stdin exit-0; relative-path resolution.
- [x] Regression: protect_secrets suite green after `bash_write_targets` moved to `_drydock_common`; completion_gate suite green after the copy-and-update fix.
- [x] `python scripts/check_sync.py` → OK, 10 pairs identical (hooks are plugin-level, not scaffolded).
- [x] `python scripts/release.py --check` → OK at 0.2.1 (0.2.2 CHANGELOG entry drafted; bump is the Owner's release step).
- [x] hooks.json valid: SessionStart, Stop, and 3 PreToolUse entries; packet_guard stdin smoke — 4 malformed payload shapes all exit 0.

## Manual Checks

- [x] 3-adversary red-team BEFORE implementation; every high/medium finding is a coded defense pinned by a test. Design changes it forced: `auth` demoted from deny to warn; workflows deny only on file creation; test/fixture/example segments suppress deny; active-packet = any changes/ subdir with tasks.md (not kebab-filtered, not bare dirs); path containment via relative_to/commonpath (not startswith); casefolded segments; Bash deny-tier coverage via the shared extractor.
- [x] Confirmed the guard never emits `updatedInput` (would desync the sibling secrets guard) and the deny reason is a fixed template with the recovery command.
- [x] Confirmed fail polarity: every error path is silent-allow; the only deliberate block is the narrow deny tier.
- [x] Cross-hook bug fix verified: completion_gate persisting a nudge now preserves the packet guard's `warned` flag (regression test).

## Documentation Updates

- [x] Operator guide updated (5-hook inventory with tier semantics).
- [x] CHANGELOG `## 0.2.2 — packet guard` drafted.
- [x] Specs updated: packet-guard delta (new capability) + completion-gate delta (shared-state writer contract). Stated non-goals documented in the spec: NotebookEdit/MCP writes (mcp-ranger's domain), Bash warn tier, per-edit packet attribution.
- [x] No README change needed. Reason: agent-side behavior; operator guide + CHANGELOG cover it.

## Independent Verification

- [x] First `drydock:verifier` pass (2026-07-07) → **NOT VERIFIED** — the adversarial mandate succeeded: three reproducible wrongful-deny classes via 33 live probes: (1) ancestor-directory poisoning (project under a `migrations/` folder → every source edit denied; absolute-path classification), (2) `>` inside quoted Bash strings treated as redirection (grep patterns, commit messages denied; unconditional regex fallback), (3) non-adjacent `db`+`migrate` matching contradicting the spec. Also noted: promised MultiEdit + latency tests missing.
- [x] Fix round (implementing agent): classification moved to project-RELATIVE paths; regex fallback gated to tokenization-failure only (which exposed and fixed a pre-existing dead branch for attached `>.env` redirects); strict db+migrate adjacency; MultiEdit + latency tests added; spec text updated to match (project-relative, quoted-strings scenarios). All three classes re-probed live → warn/silent as intended, with genuine denies still firing. Suite 193 green.
- [x] Re-verification by the `drydock:verifier` subagent (2026-07-07) → **VERIFIED WITH NOTES**. All three classes confirmed DEAD via 29 live probes (ancestor project → warn with internal migrations still denying; quoted grep/commit strings silent with real redirects still denying; adjacency enforced); the fresh new-wrongful-deny hunt passed on every axis (root-edge paths, target-anchored fallback root, case/8.3 games, attached redirect forms, MultiEdit); collateral attached-redirect fix confirmed with protect_secrets green; scope clean; the packet's NOT VERIFIED history recorded unsanitized. Notes resolved after the verdict: spec quoted-`>` clause narrowed to what the tokenizer can honestly deliver (bare quoted-`">"` tokens documented as a known limitation), stale 23/188 counts corrected to 28/193, the superseded Bash decision-log row amended to deny-tier-covered/warn-tier-non-goal, and the Dockerfile prefix match tightened to the exact-name/dot-suffix family (`dockerfile_gen.py` now warns, pinned by test) — closing the verifier's future-wrongful-deny flag.

## Result

**PASS.** Implementation + verifier-driven fix round + re-verification complete: 193 tests green (28 in test_packet_guard.py incl. one regression per wrongful-deny class), check_sync green, version lockstep intact. The wrongful-deny mandate did its job end-to-end: first pass NOT VERIFIED with three real classes, fixes pinned, re-verification confirmed dead with no new regressions. Remaining (Owner-gated): the v0.2.2 cut via `release.py 0.2.2`.
