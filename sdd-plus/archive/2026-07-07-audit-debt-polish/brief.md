# Brief

## Change

audit-debt-polish

## User Need

A user discovering Drydock on the marketplace, or an agent loading its skills, should get an accurate, self-consistent picture of what the product is and how it routes work. After the v0.2.x enforcement build the front-of-house docs undersold the product ("two hooks" when there are five) and the skills layer carried small contradictions that confuse any agent reading them.

## Problem

Closes the remaining low-severity findings from the six-dimension audit (the skills-layer and docs debt), which were queued behind the enforcement work:

- README and both `CLAUDE.md` copies claimed only two hooks and told no autonomy story — the marketplace face did not match the shipped product (session-orientation, completion gate, packet guard).
- `explore` skill id collided with the `/drydock:explore` command id, producing duplicate ambiguous `drydock:explore` registrations.
- `architect` and `mcp-ranger` lacked the LITE/STANDARD/FULL graduation their peer skills have.
- Deployment / CI-CD / infrastructure implementation had no owning skill (the audit's "no skill owns deployment" gap).
- backend↔testing contradiction on manual verification; spec-sync idempotency-vs-stop-and-ask wording clash; one grammar typo (`a Owner`).

## Scope

In scope:

- README rewrite: accurate 5-hook safety layer + the "it governs itself" autonomy story.
- Rename the `explore` skill to `explore-mode` (mirroring how `spec-sync` backs `/drydock:sync`); update every skill-id reference; keep the `/drydock:explore` command unchanged.
- Add a deterministic regression test that forbids skill-id/command-id collisions and skill name/dir drift.
- Graduation notes on `architect` and `mcp-ranger`.
- Deployment/CI/infra routing made explicit and consistent across AGENTS.md (+ scaffold), the operator guide, and the backend skill.
- Hook-count correction in both `CLAUDE.md` copies (same undersell defect as the README).

Out of scope:

- Any hook/gate behavior change (this is advisory-tier + docs + one test).
- The v0.3 Owner surface.

## Acceptance Criteria

- [x] No skill id collides with a command id; a test enforces it.
- [x] `explore` skill renamed to `explore-mode` with zero orphaned skill-id references outside the frozen archive.
- [x] README names all five hooks and tells the autonomy story.
- [x] Deployment routing is stated once and identically across all governance docs (owner: `backend`).
- [x] `architect` and `mcp-ranger` carry a LITE/STANDARD/FULL graduation note.
- [x] `check_sync` 10/10; full suite green.

## Impact Areas

- Backend: none (no code paths; `backend` skill gains a deployment routing mention, authored by the Owner).
- Frontend: none.
- Data model: none.
- API: none.
- AI/model behavior: skills and routing docs an agent reads are now accurate and non-contradictory.
- Documentation: README, both CLAUDE.md, both AGENTS.md, operator guide, architect/mcp-ranger/spec-sync/backend skills.
- Operations/security: none (no guardrail behavior changed).

## Open Questions

- None. (Deployment ownership was resolved by the Owner out-of-band in favor of `backend`; this packet made the rest of the docs consistent with that decision.)
