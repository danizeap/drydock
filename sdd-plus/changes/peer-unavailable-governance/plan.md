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

## 2026-07-30 Codex-only MVP dogfood

The Owner explicitly removed Claude from the current MVP critical path. This
is a single-pilot execution of the existing packet, not a replacement peer
transport design and not a claim of cross-model agreement.

The governed plan uses this ordered phase subsequence:

1. `preflight`
2. `mutation`
3. `proof`
4. `security_review`
5. `verification`
6. `integration`
7. `complete`

The authority omits the `peer` and `cross_review` actions, and the plan omits
the `plan_peer` and `cross_review` phases. No Claude authentication, status,
critique, or usage call is part of the workflow.

The isolated mutation is limited to:

- `adapters/codex/tests/test_orchestration_control.py`
- `adapters/codex/drydock/skills/drydock-orchestrate/SKILL.md`
- `docs/AI_OPERATOR_GUIDE.md`

The worker first adds a deterministic controller regression proving that an
Owner-authorized plan without peer actions advances directly from preflight to
mutation and then through proof, LaunchGuardian, separate verification, and
integration. It then updates the shipped skill and operator guide to describe
the same phase omission and to require `peer_convergence: not_established`.

Acceptance requires the exact isolated candidate to pass the required suite,
candidate-bound LaunchGuardian, and a separate read-only Codex verifier before
fast-forward integration. The implementing pilot's own diff inspection is
evidence, not independent review. Push remains a separate normal non-force
Owner-authorized action after the integrated commit and remote baseline are
rechecked.

### First preflight result and required remediation

The first mutation admission was issued but not consumed. The runner stopped
before worktree creation and before any Codex worker or provider process
because this repository has `extensions.worktreeConfig=true` while the
optional `.git/config.worktree` file is absent. Git 2.54 returned exit 128 for
`git config --worktree --no-includes --name-only --list`.

The runner must not create Git metadata or weaken the unsafe-key check.
Instead, when worktree config is enabled it resolves the exact current
worktree Git directory, treats a missing `config.worktree` as an empty scope,
and, when present, requires a regular, single-link, non-symlink/non-reparse
file before parsing that exact file with includes disabled. Focused tests must
cover both the safe absent case and refusal of unsafe keys in the present
file. Because this changes the admitted runner mechanism, the issued admission
and workflow are not reused.
