# Decision Log

## Change

peer-unavailable-governance

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-27 | Operational peer failure enters an explicit `single_pilot` mode instead of blocking all Drydock lifecycle work. | Codex owns governance and must remain useful when Claude usage or service availability disappears; absence of a peer is not absence of Drydock. | Treat every peer failure as fatal; silently pretend Codex and Claude agreed. |
| 2026-07-27 | Only exact structured markers or explicit rate-limit phrases may produce `rate_limited`. | The previous substring test misclassified ordinary words such as `generate` and `separate`, violating the evidence rule. | Keep broad keyword matching; remove rate-limit classification entirely. |
| 2026-07-27 | Contract-invalid peer output returns to the Owner rather than continuing automatically. | Model mismatch, malformed structure, unproven cost/model, and budget violations are integrity or control failures, not ordinary unavailability. | Continue on every failure; block on every failure. |
| 2026-07-27 | Windows peer calls require a kill-on-close Job Object and bounded drain. | PATH `taskkill` and an unbounded second `communicate()` do not back a reliable lifetime claim. | Retain process-group convention; import private mutation-runner helpers. |
| 2026-07-27 | Claude usage sensing remains a separate packet with no credential access in this change. | The newly discovered OAuth endpoint is useful but conflicts with the current credential boundary and needs its own architecture decision. | Read `.credentials.json` directly as part of this bugfix. |
| 2026-07-30 | OWNER-APPROVED: finish the Codex-host MVP without Claude in the critical path. | After repeated peer transport failures, the Owner explicitly directed Codex to stop using Claude and finish the MVP itself. The controller already supports ordered phase subsequences, so the governed workflow can omit `plan_peer` and `cross_review` without weakening isolated mutation, deterministic proof, LaunchGuardian, separate Codex verification, integration, or push checks. | Spend more Claude usage repairing the peer transport first; delete the optional adapter; bypass the remaining non-peer gates. |
| 2026-07-30 | DOGFOOD PREFLIGHT BLOCKER: inspect an existing worktree config file rather than invoking an absent optional scope. | The first Codex-only mutation admission reached the runner, but no worker or provider started because Git 2.54 returned fatal for `git config --worktree` when `extensions.worktreeConfig=true` and `.git/config.worktree` was absent. Absence carries no keys and is safe to skip; an existing file must be type-checked and parsed directly with includes disabled. | Create an empty Git metadata file; disable `extensions.worktreeConfig`; accept exit 128 generically; bypass the preflight. |
