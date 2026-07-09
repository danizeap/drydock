# Plan

## Change

consequence-approvals

## Approach

Prose + template editing, dual-copy, no code. The design is the approval-ux lens from the v0.3 Owner-surface exploration.

1. **`framework-usage.md` §7** (+ twin): replace the "Stop format" block (keep the trigger list and timing paragraphs; they are correct). New §7 body carries: the two-variant consequence template (FULL / QUICK), the fixed field order, the greppable `APPROVAL NEEDED` marker, the closed reversibility vocabulary, the "Safety net after your yes" field, and the decline path + yes/no/partial protocol. Keep it tight — this is a protocol section, not a tutorial.
2. **New `sdd-plus/templates/approval-request.md`** (+ twin): the fillable FULL and QUICK forms with inline guidance comments, so an agent copies a form rather than reconstructing it.
3. **Delta spec** `specs/approvals.md`: ADDED requirements — "Consequence-framed approval request" and "Decline path" — WHEN/THEN. Sync → `capabilities/approvals.md` (new).
4. Verify: byte-identity per pair; `check_sync.py`; pytest unchanged; framework §8 lifecycle still references APPROVE coherently; `sdd.py verify`; verifier (non-expert legibility, closed reversibility vocabulary, decline→BLOCKED mapping); sync; archive; release 0.4.2 (Owner-gated).

## Files Expected To Change

- `sdd-plus/protocols/framework-usage.md` (+ `assets/project-scaffold/` twin) — §7 rewrite
- `sdd-plus/templates/approval-request.md` (NEW, + twin)
- `sdd-plus/changes/consequence-approvals/specs/approvals.md` (delta) → `sdd-plus/specs/capabilities/approvals.md` (sync)
- `CHANGELOG.md` (at release)

## Risks

- **Alarm fatigue if the FULL ask fires on routine choices** — mitigation: the two-variant split; FULL only for the §7 trigger list (side effects + overrides), QUICK for process/plan choices.
- **Narrated reversibility** — a model free-texting "easy to undo" for a data migration is worse than no frame. Mitigation: the closed vocabulary (concrete-procedure / NOT REVERSIBLE / REVERSIBILITY UNKNOWN); the template states the model may not invent a fourth.
- **Decline that quietly becomes implementation** — mitigation: "no" → OWNER DECLINED in decision-log + stop condition mapping to the existing "a BLOCKED result is never silently converted into implementation" rule (§8).
- **Dual-copy drift** — cp root→twin, diff per pair.
- **Over-scope into the record/gate** — explicit stop condition; that is a separate red-teamed packet.

## Rollback

Additive/replacement prose + one new template. Reverting `framework-usage.md` §7 (+ twin) restores the prior stop format; the template and capability spec are deletable. No code, no data. `git revert` of the release commit is clean.
