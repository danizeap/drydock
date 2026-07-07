# Brief

## Change

owner-brief (v0.3.0) — the Owner surface, part 1 of 2.

Intake: Mode FULL (framework-level: new plugin script, new command, hook behavior additions). Primary skill: backend; supporting: testing (architect work already done via the 4-lens design exploration, synthesis on file). Approvals: design direction and build order explicitly approved by the Owner (2026-07-07, "Approve — brief first"); release remains Owner-gated. Stop conditions: any design change that would make a hook write into the project tree; any ledger append that can change a guard verdict; scope growth into the approvals template (that is v0.3.1).

## What this means for your product

After a work session you can open one file — or ask one command — and see in plain language what shipped, what's in flight, what needs you, and proof the safety net is alive, without reading code or chat history.

## User Need

Drydock persists memory for every actor except the Owner. Agents get specs, packets, and decision logs; the Owner gets a chat scroll that evaporates. A non-expert Owner wakes up with four questions — did anything move? does anything need me? did anything almost go wrong? can I still promise what I promised? — and today the answers exist only as engineer-facing state (task counts, verification Results, archive dirs) or don't exist at all: no hook records what it denied, so "what the safety net did" is forgotten at process exit. The felt product of the whole enforcement layer is invisible to the person it protects.

## Problem

1. No durable event trail: protect_secrets, git_safety, packet_guard deny and forget; completion_gate's nudges live in a session-scoped state file. Any "what the system prevented" section would confabulate or render empty.
2. No Owner-readable state: sdd.py status prints engineer shorthand about active packets only; archived (shipped) work vanishes from every status view; verification states never reach the Owner in words they can use.
3. No staleness honesty: nothing exists to stop a status document from silently lying after state moves on — and a stale "all good" is worse than nothing.

## Scope

In scope:

1. **Event ledger** — `append_event()` in `hooks/_drydock_common.py`; the four guard/gate hooks best-effort append category-only events (deny/warn/nudge) to a per-user, per-project NDJSON ledger. Appends can never affect a guard's verdict or block a session; failure degrades to "no history", never to breakage.
2. **Deterministic FACTS engine** — plugin-only `scripts/brief.py` (imports `_drydock_common`; no scaffold copy, no new check_sync pair) reading packets, archive, ledger, PROJECT_CONTEXT state; emits a structured FACTS block: each work item placed on the fixed promise ladder (idea → being built → built-not-yet-checked → independently checked → done & documented → safe for customers), provenance-classed claims (machine-enforced / independently-checked / agent's word), explicit `unavailable` markers for anything unreadable. States assigned only by code.
3. **`/drydock:brief` command** — runs the engine; the model renders the FACTS block in the Owner's own language in chat (translate-only: no new facts, absence rendered as absence, never as zero or green; every item ends in "nothing needed" or "your move: <one decision>") and writes `OWNER_STATUS.md` as an explicit, visible action — a labeled snapshot with generation date and embedded project fingerprint. Hooks never write it.
4. **Staleness sentinel** — `session_orient.py` compares the file's embedded fingerprint against freshly computed state; on mismatch adds one line inside its existing capped context so the agent offers a refresh. Read-only, fail-silent.
5. **Owner-line capture** — `commands/new.md` instructs the agent to fill the brief template's "What this means for your product" line; the engine uses it, falling back to the User Need first paragraph for older packets. `commands/archive.md` ends by offering a brief refresh.

Out of scope:

- Consequence-framed approval template, approvals.md record, archive approval gate (v0.3.1).
- Any hook writing into the project tree (spec-pinned read-only invariant stands).
- An sdd.py subcommand or scaffolded engine copy (dual-copy tax, version skew — see decision log).
- Cross-machine ledger sync (per-machine, and must be labeled as such in the brief).
- Owner-facing internals: no counts-without-baselines, no BLOCKED/NOT VERIFIED/packet/mode/skill vocabulary, no paths or content in the ledger.

## Acceptance Criteria

- [ ] All five scope items implemented with tests; full suite green; check_sync 10/10 (no new pairs).
- [ ] A guard append failure demonstrably cannot change that guard's verdict (test-pinned for all four writers).
- [ ] The FACTS block renders `unavailable` (not zero) for an unreadable ledger; the command prose forbids the model from asserting anything not in the block; the spec pins it.
- [ ] OWNER_STATUS.md is written only by the explicit command path; session_orient remains read-only toward the project tree (test-pinned).
- [ ] Promise-ladder states are assigned deterministically from packet/archive state and are wrong in neither direction on the current repo (verified against the six archived packets).
- [ ] Red-teamed before build; independent verifier review before archive.

## Impact Areas

- Backend: `hooks/_drydock_common.py` (append_event + ledger I/O), four hook files (append calls), new `scripts/brief.py`.
- Frontend: n/a.
- Data model: new per-user NDJSON ledger file format (category-only; documented in the capability spec).
- API: new `/drydock:brief` command; `commands/new.md` + `commands/archive.md` prose additions.
- AI/model behavior: brief rendering rules (translate-only) in the command file.
- Documentation: operator guide (component inventory, new section for the brief), README (Owner surface paragraph), CHANGELOG at release.
- Operations/security: ledger is category-only (no paths/content/secrets), per-user dir with the existing hashed-name + size-cap discipline; appends swallow all errors.

## Open Questions

- None blocking. Deferred by design: whether packet_guard's deny classes should later require an approvals.md entry (v0.3.1 decision, wrongful-deny discipline applies).
