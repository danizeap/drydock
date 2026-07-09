# Verification

## Change

consequence-approvals

## Automated Checks

- [x] Dual-copy byte-identity — `framework-usage.md` and `approval-request.md` each identical to their `assets/project-scaffold/` twin (diff -q), before and after the fix round.
- [x] `python scripts/check_sync.py` — OK **11/11** (the new `approval-request.md` was added to the guarded pairs to match its six template siblings, resolving verifier note #4).
- [x] `python -m pytest tests/ -q` — 251 passed, 2 skipped (the only code touched was one line in `check_sync.py`'s PAIRS list; the count is dynamic, no test hardcodes it).
- [x] Header/Undo consistency — ternary header `[CANNOT BE UNDONE | UNDO UNCERTAIN | undoable]` present in both files and twins; the old binary header and the buggy "otherwise undoable" mapping are grep-confirmed GONE from all reader-facing content.
- [x] Greppable marker `APPROVAL NEEDED` present; §8 lifecycle APPROVE reference intact; the §7 trigger list, timing, and "only the Owner authorizes" paragraphs preserved.
- [x] `python scripts/sdd.py verify consequence-approvals` — passes after this record is filled.

## Manual Checks

- [x] Non-expert legibility (the point of the change): plain referents required and jargon barred; the closed reversibility vocabulary is explicitly closed ("one of the three values above and nothing else"; "Never invent a fourth"); the "Safety net after your yes" field is present; the two-variant FULL/QUICK split is concrete.
- [x] Decline path maps to existing semantics — "no" → OWNER DECLINED in decision-log + stop condition + BLOCKED at verify (reuses §8), with the anti-nag rule, questions-never-advance, conditional-resets-once, per-action/no-generalize/restate-after-token — all present in both §7 and the template.
- [x] Scope — deferred Tier-3 enforcement (approvals.md record + sdd.py archive gate) NOT implemented, per the stated stop condition; no hook change, no CLI touch.

## Documentation Updates

- [x] README or user-facing docs updated, if needed. (This IS a protocol/template change: framework-usage.md §7, new approval-request template, + scaffold twins.)
- [x] Project context updated, if needed. (Not needed.)
- [x] Specs updated, if needed. (New `capabilities/approvals.md` living spec.)
- [ ] No documentation update needed. Reason: n/a.

## Independent Review

`drydock:verifier`, non-expert prose-quality as the highest bar. **VERIFIED WITH NOTES.** Every stated claim confirmed (two-variant template in place, reversibility vocabulary genuinely closed with an explicit ban on a fourth value, "safety net after your yes" present, decline path maps to existing BLOCKED semantics with the full anti-nag ruleset, byte-identity, 251/2 tests, scope clean — no deferred enforcement, no code beyond the check_sync pair, no hook/CLI creep). Four notes, all resolved before archive:

1. **(substantive) Reversibility header collapsed toward reassurance** — the binary header `[CANNOT BE UNDONE | undoable]` routed `REVERSIBILITY UNKNOWN` → "undoable" in the most prominent line, the exact false-reassurance the change exists to prevent. **Resolved** → ternary header `[CANNOT BE UNDONE | UNDO UNCERTAIN | undoable]`; UNKNOWN maps to "UNDO UNCERTAIN", never "undoable"; the header↔Undo mapping is now stated in §7 itself (not only the template).
2. **(minor) Partial-approval affordance had nothing to number** — `approve <numbers>` but no numbered list. **Resolved** → both §7 and the template instruct that a multi-action ask numbers its items (split past ~4), giving partial approval something to reference.
3. **(cosmetic) Casing drift** "exactly one of" vs "EXACTLY ONE OF". **Resolved** → aligned to lowercase.
4. **(consistency) New template not guarded by check_sync** while its six siblings are. **Resolved** → added to PAIRS (now 11/11).

Re-checked after the fixes: twins identical, ternary header everywhere with no binary/legacy remnant, check_sync 11/11, suite 251/2.

## Result

PASS. Verifier VERIFIED WITH NOTES; all four notes resolved, including the substantive reversibility-header fix that restored the change's own anti-false-reassurance goal. Byte-identity 2/2, check_sync 11/11, suite 251/2, scope clean.
