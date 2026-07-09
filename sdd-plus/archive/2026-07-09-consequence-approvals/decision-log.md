# Decision Log

## Change

consequence-approvals

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-09 | Ship the template + protocol (Tiers 1–2) now; defer the approvals.md record + sdd.py archive gate (Tier 3) to its own packet | The record/gate is deterministic-enforcement tier — the highest rigor bar, deserving a dedicated red-team; the template is the user-facing heart and is pure prose. Splitting delivers the felt value now without rushing an enforcement change at the end of a long session | One big packet incl. the gate (rejected: mixes prose with deterministic-tier code that needs red-team; larger review surface) |
| 2026-07-09 | Two variants — FULL consequence ask and QUICK 3-line ask | One format for everything trains click-through; a routine "archive unsynced?" must not carry the same weight as "delete production data" (the alarm-fatigue failure the exploration named) | Single format (rejected: alarm fatigue); severity levels beyond two (rejected: over-engineered for a non-expert) |
| 2026-07-09 | Closed reversibility vocabulary: Undo is exactly {concrete procedure in the plan / NOT REVERSIBLE / REVERSIBILITY UNKNOWN} | "Narrated reversibility" — a model free-texting "easy to undo" for a destructive action — is the most dangerous sentence in an approval, and worse than no frame because the frame vouches for it | Free-text undo field (rejected: hallucinated reversibility); omitting undo (rejected: it is the single most calming, most decision-relevant datum) |
| 2026-07-09 | Add a "Safety net after your yes" field (novel) | This is where the enforcement layer becomes felt per-decision — "even if this goes wrong, the secrets and git guards still hold" vs "nothing automatic catches this past here" teaches the Owner where the floor is | Omitting it (rejected: loses the one field that makes the guardrails legible at the decision moment) |
| 2026-07-09 | Header is a stable, greppable marker (`APPROVAL NEEDED`) | The header doubles as an API for a future Tier-4 Stop-hook that detects an approval moment with no subsequent yes token; keeping it stable and greppable is a cheap design requirement now | An unmarked prose ask (rejected: nothing for a future hook to detect) |
| 2026-07-09 | Decline path maps onto existing BLOCKED semantics, with an anti-nagging rule | Reuses "a BLOCKED result is never silently converted into implementation" (§8) rather than inventing new machinery; the anti-nag rule (≤2 alternatives once, never the identical re-ask) mirrors packet_guard's warn-once philosophy | Inventing a new decline state (rejected: duplicates BLOCKED); no anti-nag rule (rejected: re-asking a declined question until the Owner relents is the chat equivalent of retrying a blocked hook) |
