# Brief

## Change

consequence-approvals (v0.4.2) — the Owner surface, part 2: approvals in plain language.

Intake: Mode FULL (framework-level change to the approval protocol). Primary skill: none (protocol/prose editing); the design came from the v0.3 Owner-surface exploration (approval-ux lens). Approvals: Owner authorized proceeding through the roadmap ("do all the next steps"). Stop conditions: the deterministic enforcement layer (per-packet `approvals.md` record + an `sdd.py` archive gate) is deliberately OUT of scope for this packet — it is a deterministic-tier change that deserves its own red-team; this packet ships the template + protocol (Tiers 1–2). No hook changes.

## What this means for your product

When the AI needs your permission for something risky, it now asks in plain language with the consequences spelled out — what changes, what could go wrong, whether it can be undone, and what safety still protects you after you say yes — instead of a jargon prompt you'd rubber-stamp.

## User Need

Drydock defines ~25 approval triggers (destructive migrations, data deletion, deploys, payments, permission changes, external messages, breaking APIs — `framework-usage.md` §7, mcp-ranger's matrix, database-steward, backend). Today the agent improvises the ask as chat prose, and the §7 stop format a non-expert actually sees is four neutral fields (Decision / Why / What happens / Awaiting). That hands a non-expert a decision they can't evaluate: no undo statement, no blast radius, no "what could go wrong" in outcome terms, no signal of which safety still applies after yes. The rational responses are to rubber-stamp everything or freeze — and rubber-stamping is the erosion the project already named for blanket `--force`. Every boilerplate approval burns trust; the scarcest resource in the product is Owner attention that still means something.

## Problem

1. The §7 stop format is jargon-tolerant and consequence-light: nothing stops the agent writing "Decision: approve destructive migration with RLS policy change" — the exact failure the Owner surface exists to kill.
2. No **undo** field, and nothing constrains the model from free-texting a comforting but false "easy to undo" (narrated reversibility is the most dangerous sentence a model can put in an approval).
3. No **"what still protects you after yes"** signal — the one place the enforcement layer becomes felt per-decision.
4. No plain-language **decline path**: the framework defines approval but not "no" — how it's recorded, what it blocks, and the anti-nagging rule.
5. One format for everything invites alarm fatigue — a routine "archive unsynced?" reads with the same weight as "delete production data", and within a week the Owner swipes past the real one.

## Scope

In scope (framework prose + a template; each in root and `assets/project-scaffold/` twin):

1. **Replace `framework-usage.md` §7 stop format** with a two-variant consequence-framed template:
   - **FULL ask** (side effects + gate overrides), ≤12 lines, fixed field order: What I want to do (plain referents) / Why I'm asking you (plain risk category) / What could go wrong (worst realistic, concrete) / Who or what is affected (this code | your data | people outside) / **Undo** (closed vocabulary — see below) / **Safety net after your yes** / options block.
   - **QUICK ask** (process/plan choices like archive-unsynced), 3 lines: What / Why you / approve-or-no.
   - A stable, greppable header marker (`APPROVAL NEEDED`) — a future hook API.
   - **Closed reversibility vocabulary**: Undo is exactly one of `a concrete procedure named in the plan` / `NOT REVERSIBLE` / `REVERSIBILITY UNKNOWN` — the model may not free-text a fourth.
   - The yes/no/partial protocol + the **decline path** (no → OWNER DECLINED in the packet's decision-log, becomes a stop condition mapping to BLOCKED; ≤2 alternatives offered once; never the identical re-ask; questions never advance state; conditional yes resets the ask once; a yes never survives the session or generalizes past the stated action; the agent restates what was approved after the token).
2. **New template** `sdd-plus/templates/approval-request.md` — the fillable FULL/QUICK forms.
3. **Delta spec** `specs/approvals.md` (new `approvals` capability) → `capabilities/approvals.md`.

Out of scope (deferred, documented):

- The `approvals.md` per-packet record + `sdd.py` archive gate + verifier cross-check (Tier 3 enforcement — its own red-teamed packet, since deterministic-tier changes carry the highest rigor bar).
- Any hook (Tier 4 marker/token detection).
- The CLI (parked).

## Acceptance Criteria

- [ ] §7 carries the two-variant consequence template with the fixed field order, the greppable marker, the closed reversibility vocabulary, the "safety net after yes" field, and the full decline path.
- [ ] `sdd-plus/templates/approval-request.md` exists with both forms.
- [ ] Every edited/new file byte-identical to its scaffold twin.
- [ ] `check_sync.py` 10/10; full pytest suite unchanged (no code); framework internally consistent (the §7 rewrite doesn't break §8 lifecycle references to APPROVE).
- [ ] Delta spec written and synced; `sdd.py verify`/`archive` gates pass; verifier confirms the template is non-expert-legible, the reversibility vocabulary is genuinely closed, and the decline path maps to existing BLOCKED semantics.

## Impact Areas

- Backend/Frontend/Data/API/AI: none (protocol/prose; governs how agents ask a human for approval).
- Documentation: `framework-usage.md` §7 (+ twin), new approval-request template (+ twin), new capability spec.
- Operations/security: approvals are a security-relevant control — FULL mode.

## Open Questions

- None blocking. Deferred: the deterministic `approvals.md` record + archive gate (own packet); whether the QUICK ask should also be recorded (decide with the record packet).
