# Verification

## Change

gate15-lethal-trifecta

## Automated Checks

- [x] Dual-copy byte-identity — all 4 twinned files (`launchguardian-framework.md`, `security-shipping-standards.md`, `gate-applicability.template.yml`, `gate-applicability.output.template.yml`) confirmed identical between root and `assets/project-scaffold/` (diff -q), before AND after the fix round.
- [x] YAML validity — both applicability templates and their twins parse (`yaml.safe_load`), including the new `lethal_trifecta` blocks (reusable + worked example) nested under the Gate 15 entry.
- [x] `python scripts/check_sync.py` — OK 10/10 (edited files are not among the guarded pairs; stayed green).
- [x] `python -m pytest tests/ -q` — 251 passed, 2 skipped (unchanged; no code touched).
- [x] Gate integrity — 22 gates (0–21), no renumbering; the new `## Gate 15 — the Lethal-Trifecta Test` is a markdown subsection, not a 23rd gate (the only "Gate 22" in the tree is the rejected alternative in the decision log). Gate name "Gate 15 — AI/RAG/Agent Security" identical across framework spec, standards, both templates, and the applicability-system spec.
- [x] `python scripts/sdd.py verify gate15-lethal-trifecta` — passes after this record is filled.

## Manual Checks

- [x] Faithfulness to the CONFIRMED research (the highest bar): the three legs, the structural root cause, and the `service_role`-bypasses-RLS claim map exactly to the [3-0]/[2-0] verified findings. The refuted "1 in 9 / 11.04%" statistic is absent.
- [x] Scope discipline — every added gate-referencing line names only Gate 15 (verifier: 14 occurrences, 0 others); no Gate 6/10/16, CI/CD, supply-chain, slopsquat, Stripe, or OWASP-2025 content leaked in.
- [x] Delta ⇄ capability — the ADDED requirement text is identical in the delta and the synced `capabilities/launchguardian.md`; the capability Purpose defers to the framework spec (no gate-content duplication).

## Documentation Updates

- [x] README or user-facing docs updated, if needed. (This IS a docs/spec change: LGF framework spec, security-shipping standards, both applicability templates + scaffold twins, new living capability spec.)
- [x] Project context updated, if needed. (Not needed.)
- [x] Specs updated, if needed. (Framework spec + new capability spec; the v0.4 research note was corrected — see below.)
- [ ] No documentation update needed. Reason: n/a.

## Independent Review

`drydock:verifier`, adversarial mandate with faithfulness as the highest bar. **VERIFIED WITH NOTES.** Every mechanical/structural claim CONFIRMED (byte-identity 4/4, check_sync 10/10, pytest 251/2, valid YAML under the correct gate, 22 gates intact, name consistency, delta==capability, valid mcp-ranger reference, clean Gate-15-only scope). Four notes, all resolved before archive:

1. **(material) OAuth/session-tokens provenance gap** — the framework's most specific detail ("a table of OAuth/session tokens") had no source in the repo's own research note, which I had summarized down to "exfiltrates the database." The detail is genuinely part of the CONFIRMED [3-0] claim (the `integration_tokens` table). **Resolved** by restoring the detail to the research note (`launchguardian-v0.4-gap-research.md`) with its [3-0] marker, so the framework claim is now sourced — the honest fix, since the detail is true and verified (softening would have discarded real information).
2. **(calibration) read-only clause over-confident** — asserted as flat fact though it sat in the note's un-voted Implication tier. **Resolved** by rewriting it from assertion to stated mechanism ("read-only governs database *writes*, whereas the exfiltration path is *reading* + injection + outbound — none of which read-only prevents").
3. **(minor) worked example not updated** — the example AI-app matrix entry didn't demonstrate the new field. **Resolved** by adding a filled `lethal_trifecta` block (all three legs present, outbound leg broken, with a mitigation).
4. **(minor) plan/brief field wording vs shipped shape** — **Resolved** with a decision-log row recording the final tri-state `broken_leg`+`mitigation` shape and why (matches the gate-level `applies` style; the YAML is a record, not a rules engine).

## Result

PASS. Verifier VERIFIED WITH NOTES; all four notes resolved, faithfulness restored (the one alarming detail now sourced, the one over-confident clause recalibrated). Re-checked after the fix round: byte-identity 4/4, YAML valid, check_sync 10/10, suite 251/2, Gate-15-only scope intact.
