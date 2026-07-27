# Brief

## Change

peer-unavailable-governance

## User Need

Drydock must remain the active Codex-hosted governor when the configured
Claude peer is absent, out of usage, timed out, or temporarily unavailable.
The Owner must be able to keep working without a failed peer call being
mistaken for either cross-model agreement or a total loss of governance.

## Problem

The Codex orchestration spec already makes Claude optional, but the shipped
`drydock-orchestrate` skill still instructs Codex to call Claude
unconditionally and gives no machine-readable continuation decision when the
peer is unavailable. The adapter also classifies any failure text containing
the substrings `rate`, `quota`, or `usage` as rate limiting, so unrelated text
such as `generate` or `separate` can produce a false quota diagnosis.

Finally, timeout cleanup uses a PATH-resolved `taskkill`, can skip descendants
after the direct child exits, and performs an unbounded second output drain.
That is weaker than the process boundary already required elsewhere in the
Codex host.

## Scope

In scope:

- A conservative peer-failure classifier based on exact structured markers or
  explicit whole failure phrases.
- A machine-readable decision that separates Codex-only continuation from
  contract failures that must return to the Owner.
- Shipped skill and operator guidance for the single-pilot path.
- Bounded peer-process cleanup, including a Windows kill-on-close Job Object
  and bounded post-timeout output drain.
- Deterministic fake-CLI tests that spend no model quota.

Out of scope:

- Reading Claude credentials or calling Anthropic's private usage endpoint.
- Claiming that authentication status proves operational capacity.
- Replacing the independent verifier or weakening any packet, approval,
  LaunchGuardian, integration, or release gate.
- Automatic retry loops, model fallback, merge, push, release, or archive.
- A Claude-usage forecasting implementation; that is a separate packet.

## Acceptance Criteria

- [ ] Operational peer failures explicitly permit governed Codex-only
  continuation while recording that peer convergence was not established.
- [ ] Malformed, mismatched, over-budget, or otherwise contract-invalid peer
  results stop and return to the Owner.
- [ ] Unrelated words containing `rate`, `quota`, or `usage` cannot be
  classified as rate limiting.
- [ ] Exact supported rate-limit markers remain recognizable without exposing
  raw peer output.
- [ ] Timeout cleanup is bounded and a real delayed descendant cannot create
  its sentinel after the peer times out.
- [ ] Documentation never calls single-pilot work two-brain convergence or
  independent cross-model review.
- [ ] Focused and adapter-wide tests pass without a live Claude call.

## Impact Areas

- Backend:
- `adapters/codex/drydock/scripts/orchestrator.py`
- Frontend:
- None.
- Data model:
- None.
- API:
- Adds a `workflow` decision to failed negotiation results.
- AI/model behavior:
- Claude remains optional; no fallback or retry is inferred.
- Documentation:
- Codex orchestration skill and operator guide.
- Operations/security:
- Peer subprocess lifetime and failure classification.

## Open Questions

- A credential-free machine-readable Claude usage source remains unavailable;
  the separate `claude-usage-signal` packet will preserve that boundary.
- POSIX process groups remain a best-effort descendant cleanup mechanism;
  this packet does not claim hostile descendant containment there.
