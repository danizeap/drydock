# Brief

## Change

codex-host-mvp

## User Need

The Owner needs one Drydock pilot across all repositories. Codex should host
the governance lifecycle and orchestration so work does not become ungoverned
when Claude usage is exhausted. Claude/Fable should remain an equal planning
and review peer when available, without becoming a runtime prerequisite for
governance.

## Problem

The working product is packaged and wired for Claude Code. The original Codex
port proposal incorrectly treated the current conductor as host-neutral,
treated skills as command equivalents, and overstated ordinary Codex plugin
hooks as a non-bypassable Tier-4 boundary.

Platform spikes also proved that hook trust does not cover handler source
changes and that a nested custom verifier inherits a write-capable parent's
live permission override. Cross-model review then found that the first
blueprint omitted mutating worktree containment, left a verify-then-import
file-swap race, and treated Claude-specific/stateful hook entry points as
host-neutral policy. A second cross-model review then caught that nested
write-capable agents still could not enforce the claimed worktree boundary
because their permissions inherit live parent overrides.

## Scope

In scope:

- Additive Codex plugin packaging and workflow skills.
- Codex-native hook wiring, Windows support, active-task readiness, and honest
  enforcement profiling.
- Reuse of the shared SDD+ lifecycle and only independently tested pure policy
  primitives; host-native dispatch and state machines.
- Project-scoped advisory agents plus pace-aware, right-sized mutating workers
  launched as separate fixed-root processes with one exclusive lease per
  worktree/task branch.
- A separate fixed read-only verifier process bound to a repository
  fingerprint.
- A host-neutral orchestration controller and optional Claude peer adapter.
- Contract, negative-permission, live opt-in, and cross-platform tests.
- Documentation and LaunchGuardian review for the new security boundary.

Out of scope:

- Replacing or breaking the existing Claude plugin.
- Managed enterprise hooks/MDM distribution.
- Claiming full tool coverage or non-disableable enforcement.
- An SDD+ MCP server.
- Automatic merge, push, deploy, or publication.
- Undocumented plugin packaging for custom agents.

## Acceptance Criteria

- [ ] One Codex plugin installation provides the host skills and hook
  definitions; per-repository initialization is explicit.
- [ ] Readiness distinguishes installed, trusted, active in this task,
  initialized, managed/non-managed, covered/uncovered, and peer availability.
- [ ] Codex guards deny the supported secret/destructive-git/packet cases on
  Windows and POSIX without relying on Claude tool names.
- [ ] Trusted hook commands contain the verifier program and canonical mutable
  handler-bundle digest; the runtime bytes are read once, verified, and
  executed from memory under isolated/no-site startup with repository/plugin
  imports pinned out; the normalized plain-source bundle rebuilds byte-for-byte
  in CI and legitimate changes force a new trust review.
- [ ] Narrow matchers intercept only supported side-effect contracts; a
  mismatch inside a matched hook fails closed, unmatched tools remain
  unintercepted and explicitly uncovered, and stateful packet/orientation/
  completion behavior uses Codex-native adapters.
- [ ] Lifecycle skills invoke the authoritative SDD+ procedures without
  claiming slash-command parity.
- [ ] The independent verifier runs in a separate ephemeral read-only process
  and invalidates its verdict if the repository fingerprint changes.
- [ ] Project-scoped execution agents use the configured model tiers, but are
  not treated as an isolation boundary.
- [ ] Mutating execution uses a separate ephemeral process with a fixed
  workspace-write root, never writes in the Owner checkout, never shares a
  leased worktree between writers, safely reclaims only dead stale leases,
  leaves Git metadata mutation to the runner, invalidates on Owner-state drift,
  never auto-merges, and never reports timed-out or untrusted evidence as
  green.
- [ ] Claude peer availability/authentication/failure is structured and never
  silently presented as two-brain agreement.
- [ ] Read-only process isolation and cross-model epistemic review are reported
  as distinct properties.
- [ ] The current Claude plugin and full existing test suite remain green.
- [ ] LaunchGuardian records the hook, agent, peer, and supply-chain boundary.

## Impact Areas

- Backend: plugin/runtime discovery, subprocess adapters, hook dispatch,
  verifier runner, orchestration controller.
- Frontend: Codex skill UX and readiness output only.
- Data model: local structured readiness/peer/verifier envelopes; no database.
- API: new host, peer, and verifier adapter contracts.
- AI/model behavior: Codex becomes pilot; Claude becomes an optional peer;
  right-sized Codex execution agents.
- Documentation: blueprint, operator guide, setup, capability specs, enforcement
  vocabulary.
- Operations/security: plugin trust, hook coverage, handler upgrade integrity,
  read-only verifier isolation, optional external peer egress.

## Open Questions

- Claude authentication and the exact Opus 5 two-turn structured transport
  path are proven. The full high-effort CLI review exceeded its 180-second
  wrapper deadline, while the Owner-relayed review of the same corrected
  architecture returned convergence with no blockers. Runtime readiness must
  preserve timeout as an explicit unavailable state rather than treating the
  interactive review as transport evidence.
- The exact measured forecast for the Owner's roughly three-hour coding pace
  reserve remains to be designed; missing evidence must report unavailable.
- Managed hooks may become a separate enterprise edition/profile later; they
  are not required for this MVP.
