# Decision Log

## Change

completion-integrity

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-07 | Nudge at most ONCE per session, session-global | The Stop hook's only options are silence or forced continuation (docs-confirmed); more than one forced continuation per session is a trap, not a nudge. The archive gates remain the hard backstop. | Per-packet nudges (rejected: multi-packet sessions could chain interruptions); nudge every stop while unverified (rejected: infinite-loop-adjacent, adoption poison). |
| 2026-07-07 | Set `nudged:true` BEFORE emitting the block | If the flag write fails after speaking, the next stop would nudge again → loop. Writing first means a persistence failure degrades to silence, never repetition. | Write after emit (rejected: loop on write failure); no persistence, rely on an undocumented stop_hook_active flag (rejected: not in the docs; honored defensively if present but never relied on). |
| 2026-07-07 | "Work happened" = packet fingerprint changed since SessionStart | Deterministic, cheap, project-read-only; ties the nudge to actual packet activity this session rather than mere packet existence (orient already reports existence at start). | Parsing the transcript for completion claims (rejected: heuristic, fragile, privacy-adjacent); git diff (rejected: conflates out-of-session changes; slow on big repos); nudging whenever verification is Pending (rejected: fires on pure conversation). |
| 2026-07-07 | State file in OS temp dir, project tree stays read-only | The hooks' read-only-project invariant is load-bearing (spec'd in v0.2.0); a transient per-session temp file keeps that while giving the two hooks a channel. | Writing state into sdd-plus/ (rejected: mutates the user's project from a hook); env vars (rejected: hooks are separate processes); no state (rejected: loop prevention is mandatory, docs provide none). |
| 2026-07-07 | Fail direction is ALWAYS silent-allow | A completion nudge is advisory tier-4; a false block/loop is catastrophic for adoption while a missed nudge costs nothing (archive gates still catch it). Opposite polarity from the guards, deliberately. | Fail-closed like git_safety (rejected: wrong asymmetry — here the harm of false positive far exceeds false negative). |
| 2026-07-07 | Nudge wording offers the deferral path | "Run /drydock:verify <x> OR explicitly tell the Owner why verification is deferred" — the gate enforces the *conversation*, not obedience; the Owner can always decline. | Hard "must verify" wording (rejected: overrides Owner authority; trains --force-style resentment). |
| 2026-07-07 | Work with no packet at all is a stated non-goal here | Detecting ungoverned work is PreToolUse territory (v0.2.2); this gate governs claimed-done-but-unverified packet work only. | Stretching this hook to detect packetless work via git status (rejected: scope creep, false positives on user's own edits). |
