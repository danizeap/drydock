# Plan

## Change

peer-unavailable-governance

## Approach

# Backend Change Plan

Classification: AI integration and subprocess lifecycle.

Existing pattern found: `ClaudePeer` owns authentication and one bounded
critique call; `NegotiationController` owns workflow interpretation; focused
tests use `fake_claude.py` through the real subprocess path without network or
quota. The mutation runner already demonstrates Windows kill-on-close Job
Objects, but this packet keeps the peer lifecycle adapter-owned.

1. Add a pure failure-classification helper that trusts exact structured
   subtype values first and otherwise matches only explicit rate-limit
   phrases in the result field. Never classify from arbitrary substring
   fragments or stderr usage text.
2. Add a pure peer-failure workflow decision. Operational availability stages
   return `continue_codex_only`, `single_pilot`, and
   `peer_convergence: not_established`. Contract-integrity stages return
   `return_to_owner` and never authorize execution.
3. Attach that decision to failed `NegotiationController.one_round()` results
   while preserving non-zero CLI exit status for a failed peer call.
4. Start Windows peer processes suspended, assign them to a kill-on-close Job
   Object, then resume. Fail closed if that boundary cannot be established.
   On timeout, terminate the supported boundary and use a bounded output drain.
   POSIX continues to use a new session/process group and reports its
   best-effort limitation.
5. Extend the fake CLI and focused tests with exact/false rate-limit messages,
   availability-versus-contract workflow decisions, and a real delayed
   descendant sentinel.
6. Update the shipped orchestration skill and operator guide so Codex follows
   the returned decision without claiming peer agreement.

## Files Expected To Change

- `adapters/codex/drydock/scripts/orchestrator.py`
- `adapters/codex/drydock/skills/drydock-orchestrate/SKILL.md`
- `adapters/codex/tests/fake_claude.py`
- `adapters/codex/tests/test_orchestrator.py`
- `docs/AI_OPERATOR_GUIDE.md`
- This change packet and one delta spec.

## Risks

- A permissive continuation rule could bypass a real peer-contract defect.
  Only explicit operational-availability stages continue; contract failures
  return to the Owner.
- Text classification can drift with Claude CLI wording. Exact structured
  markers are preferred; phrase fallback is narrow and tests reject substring
  collisions.
- Windows Job Object setup is platform-specific. Failure to establish it
  refuses the peer process instead of silently falling back.
- Timeout cleanup and final output drain can exceed the requested peer
  deadline by a small bounded cleanup allowance; evidence names that margin.
- POSIX process groups do not prove containment against a hostile process that
  deliberately escapes its group.

Stop conditions: unexpected files, live model calls, credential access,
unbounded cleanup, failing tests, or a result shape that can be read as
cross-model agreement without a valid critique.

## Rollback

Revert the packet's source, skill, test, and documentation commit. The prior
adapter behavior returns, with no data migration, credential change, plugin
installation, or external state to unwind.
