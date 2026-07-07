# Brief

## Change

packet-guard

## User Need

The last enforcement brick of the autonomy vision: catching **ungoverned work**. Both prior slices honestly declared this gap — the orientation hook tells the agent about packets, the completion gate polices claimed-done packet work, but an agent that implements meaningful changes with *no packet at all* (the canonical novice failure) is invisible to the deterministic tier until archive time — which ungoverned work never reaches.

## Problem

1. **Nothing enforces packet discipline in the loop.** `/drydock:new` is advisory (tier 1/2). An agent can edit source, migrations, auth code, or CI workflows all day with zero governance and no deterministic signal.
2. **The platform shapes the solution.** PreToolUse supports deny-with-reason and (docs-confirmed) warn-but-allow via `additionalContext` on `permissionDecision: allow` — the model sees the note next to the tool result. `ask`/`defer` are under-documented and deliberately not used.
3. **The false-positive stakes are the highest of any hook yet.** This fires on every Write/Edit in every Drydock project, and legitimate LITE work (typos, docs, small known-file edits) is *allowed* to happen without a packet by Drydock's own framework rules. A guard that wrongly denies or nags becomes the erosion dynamic the audit warned about.

## Scope

In scope (v0.2.2):

- `hooks/packet_guard.py` (new, PreToolUse on Write|Edit|MultiEdit): risk-tiered response to edits when no active packet exists:
  - **Silent** — non-Drydock project; target outside the project root; an active packet exists; exempt paths (sdd-plus/ itself, .claude/, *.md, LICENSE, .git*).
  - **Warn-once** (allow + additionalContext, once per session via the v0.2.1 state channel) — in-project source edit with no active packet; message notes `/drydock:new` for meaningful work and explicitly blesses trivial LITE edits.
  - **Deny** (permissionDecision deny + reason) — no active packet AND a narrow high-risk path (exact segments like `migrations`/`auth`, `.github/workflows/`, Dockerfiles). Recoverable: open a packet and retry.
- Wire hooks.json; tests for every false-positive class the red-team finds; CI smoke; operator guide + CHANGELOG 0.2.2.
- Red-team before implementation (running); findings become defended scenarios. Final tier lists are set by the red-team results.

Out of scope (stated non-goals):

- Bash-mediated writes (echo/sed/tee) — per-edit shell parsing for governance is false-positive-prone; the completion gate + archive gates + orientation remain the net. Revisit only with evidence.
- Per-edit packet *attribution* (any active packet = governed).
- Judging whether work *should* be LITE vs packet-worthy (the warn text educates; skills govern).
- The Owner surface (v0.3).

## Acceptance Criteria

- [ ] Every red-team high/medium false-positive scenario is defended and pinned by a test.
- [ ] Legit flows never denied: docs/LITE edits silent; packet-active sessions silent; out-of-project writes (scratchpad/temp) silent.
- [ ] Warn fires at most once per session; deny only on the narrow high-risk list with no active packet.
- [ ] Any error/malformed input → silent allow, exit 0 (never breaks an edit).
- [ ] State-file schema stays compatible with v0.2.1 (completion gate unaffected).
- [ ] pytest green, check_sync green; adversarial verifier review (false-positive mandate).

## Impact Areas

- Backend: new PreToolUse hook; small optional `warned` flag in the session state schema.
- Frontend: none.
- Data model: none beyond the optional state-file flag.
- API: hooks.json gains a third PreToolUse entry.
- AI/model behavior: at most one ungoverned-work note per session; denials only on high-risk paths, with a recovery path in the reason.
- Documentation: operator guide (5-hook inventory, tier semantics), CHANGELOG 0.2.2.
- Operations/security: closes the ungoverned-work gap declared in v0.2.0/v0.2.1; per-edit latency budget must stay trivial.

## Open Questions

- Final deny-list contents and exempt-list contents — deliberately left to the red-team findings before implementation.
