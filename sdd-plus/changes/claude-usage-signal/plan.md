# Plan

## Change

claude-usage-signal

## Approach

This is a design checkpoint, not implementation authorization. The Build
Blueprint is in `build-blueprint.md`.

1. Freeze a small sanitized snapshot contract independent of Anthropic's raw
   response schema.
2. Make the first provider an Owner-supplied or external local broker that
   writes or emits only that sanitized contract. Drydock does not receive,
   refresh, or locate credentials.
3. Add an explicit manual snapshot path so routing can use honest Owner-provided
   values before automation exists.
4. Feature-detect a future official Claude structured usage command rather
   than assuming one. Absence is `unavailable`.
5. Validate schema, numeric ranges, timestamps, freshness, future skew, and
   supported attribution. Reject unknown fields and never preserve a raw
   provider response.
6. Cache only the sanitized snapshot with a short TTL. Respect provider
   backoff/`Retry-After` through the broker contract and poll at decision
   points, not continuously.
7. Feed valid remaining/reset evidence into pace forecasting. Keep measured
   burn separate: two snapshots can estimate shared-account burn, but cannot
   attribute consumption to Drydock, Codex, a model, or a particular chat.
8. Add fixtures and fake brokers only. No CI or unit test may read credentials
   or call Anthropic.
9. Before implementation, obtain the Owner's provider choice and a Claude peer
   review. If the choice involves credentials, create a separate explicit
   credential-boundary packet.

## Files Expected To Change

Design-only packet:

- `sdd-plus/changes/claude-usage-signal/brief.md`
- `sdd-plus/changes/claude-usage-signal/build-blueprint.md`
- `sdd-plus/changes/claude-usage-signal/evidence.md`
- `sdd-plus/changes/claude-usage-signal/specs/claude-usage-signal.md`
- packet task, decision, and verification records

No runtime source file changes are authorized.

## Risks

- Treating a private endpoint as a product contract would create silent drift.
- Reading Claude credentials would contradict the current blueprint and widen
  Drydock's trusted computing base.
- A writable local broker snapshot can be forged or replayed. It is advisory,
  never an enforcement or authorization signal.
- Usage is account-wide. Deltas include other Claude surfaces and cannot prove
  Drydock-specific burn.
- Polling too often can itself trigger rate limiting; stale last-good numbers
  can look current unless freshness is explicit.
- A displayed Opus window does not establish a Fable-specific window.
- Remaining/reset data does not by itself establish a stable burn rate.

## Stop Conditions

Stop before implementation if it requires Drydock to read or receive a token,
if the provider contract includes raw responses, if stale data can appear
current, if advisory capacity can skip governance, or if an undocumented
endpoint is described as supported.

## Rollback

This packet creates no runtime behavior or external state. It can be abandoned
without migration or credential cleanup.
