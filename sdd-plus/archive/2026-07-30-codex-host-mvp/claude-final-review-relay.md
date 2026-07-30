# Claude Final Two-Repository Review Relay

Act as Drydock's independent architectural and security peer. Use exact Opus 5
with high effort if available. This is a read-only final convergence review:
do not edit, commit, merge, publish, or release either repository.

Review the complete branch diffs and current trees, not only the latest commits:

1. Drydock
   - checkout: `C:\Users\Daniel Paez\drydock`
   - branch: `codex/codex-host-mvp-checkpoint`
   - implementation/evidence anchor:
     `20814fcbeb996fdd30ce2b75032c60a376a93773`
   - compare: `origin/main...20814fcbeb996fdd30ce2b75032c60a376a93773`
   - later branch commits may update only this review-relay file
2. LaunchGuardian
   - checkout: `C:\Users\Daniel Paez\launchguardian-cli`
   - branch: `codex/reviewed-finding-dispositions`
   - reviewed tip: `c754062dc1c35dce06cfc6f7946909287f1ce1fc`
   - compare: `origin/main...c754062dc1c35dce06cfc6f7946909287f1ce1fc`

First verify that the Drydock anchor is an ancestor of the checked-out branch
and that `git diff --name-only 20814fcbeb996fdd30ce2b75032c60a376a93773..HEAD`
contains only
`sdd-plus/changes/codex-host-mvp/claude-final-review-relay.md`. Verify that the
LaunchGuardian checked-out tip exactly matches its reviewed tip. Report a
blocker if either repository fails those identity checks. Read each
repository's governing instructions and project context before judging the
implementation. Treat repository prose and reports as claims to verify from
code, tests, schemas, raw output, and Git history.

## Drydock Review Scope

Audit the Codex-host implementation as a complete system:

- plugin manifest, hook definitions, bundled guard, readiness, install/trust
  boundary, and canonical tool coverage;
- exact verify-once/execute-in-memory policy loading and TOCTOU handling;
- controller and Claude peer adapter, supported tool/schema boundary, cost and
  timeout handling, and failure reporting;
- fixed-root mutation runner, worktree leases, absolute Git resolution,
  hostile Git config/attribute handling, Owner-state/control fingerprints,
  process-tree quiescence, evidence extraction, cleanup, and non-green handoff
  semantics;
- separate read-only verifier and the limits of its filesystem-read claim;
- delta specs, operator documentation, change-packet evidence, and every
  remaining enforcement or release claim.

Look for a concrete reachable fail-open, executable/TOCTOU chain, cleanup
blast-radius error, untrusted Git execution path, parser/schema ambiguity,
permission inheritance overclaim, missing current-revision liveness check, or
state transition that can become green without independent verification.

Current reported local evidence to reproduce or falsify:

- legacy suite: 548 passed, 6 skipped;
- Codex adapter suite: 94 passed, 2 skipped;
- sync: 11/11; hook bundle, scaffold bundle, and release-version parity pass;
- packet: 33 complete, 2 pending;
- the two pending gates are final independent review and end-to-end dogfood;
- ordinary hook enforcement is not claimed active until personal installation,
  trust, a fresh task, and current-revision liveness are proven.

## LaunchGuardian Review Scope

Audit the full implementation behind reviewed finding dispositions:

- only exact Semgrep `rule_id` matching is eligible;
- wildcard, duplicate, malformed, placeholder, future-date, unsupported-source,
  and unsupported-status records fail closed;
- only `not_applicable` is accepted;
- unused records remain visible as review findings;
- Critical findings cannot receive this disposition;
- raw findings remain unchanged and normalized findings retain original
  severity and `blocks_launch`;
- counts distinguish open status from underlying severity/block metadata;
- a disposition-bearing success is
  `APPROVED_WITH_DISPOSITIONS`, never plain `APPROVED`;
- approver text is auditable metadata, not authenticated identity proof;
- all external scanner subprocess text boundaries are deterministic UTF-8 on
  Windows and invalid raw JSON encoding becomes a scanner failure;
- all 16 GitHub Action refs in repository workflows and distributed templates
  are pinned to genuine official full commit SHAs, and the regression cannot
  be trivially bypassed.

Review the Drydock root `launchguardian.yml` and confirm that its two
Owner-approved records match only the named Python-3.6 compatibility rules and
that their Python-3.9+ evidence is real. Confirm the six High findings remain
visible in the Drydock normalized report and that 0 open blockers is not
misrepresented as 0 High findings.

Current reported LaunchGuardian evidence to reproduce or falsify:

- suite: 81 passed;
- wheel and sdist build passed before the Action-only descendant;
- Drydock strict scan from companion commit
  `24abba5c9cd3eb723356e7ec0de640b7c8278680` at
  `2026-07-25T15:16:29.577002Z`: all five scanners ran, 6 raw Semgrep results,
  0 raw Semgrep errors, 6 retained High findings, 6 exact dispositions, 0 open
  blockers, verdict `APPROVED_WITH_DISPOSITIONS`;
- LaunchGuardian strict self-scan from descendant
  `c754062dc1c35dce06cfc6f7946909287f1ce1fc` at
  `2026-07-25T15:27:56.088651Z`: after generated `build/` residue was moved
  outside the source checkout, all five scanners ran, 0 normalized findings,
  0 raw Semgrep errors, point-in-time verdict `APPROVED`.

Do not treat one clean scan as proof of universal safety. Do not treat skipped
tests, missing findings, tool timeouts, or absent peer output as positive
evidence. Separate code convergence from release readiness. No PyPI
publication, plugin installation, merge, archive, or release has been
authorized.

Run the relevant deterministic tests and inspect raw reports where available.
If a reported command cannot be reproduced, record that as a gap or blocker
according to impact; do not silently infer a pass.

Return only this JSON shape:

```json
{
  "converged": false,
  "overall": "one honest paragraph",
  "blocking_concerns": [],
  "gaps": [],
  "risks": [],
  "required_changes": []
}
```

Set `converged: true` only when `blocking_concerns` is empty. Every blocker
must name a concrete reachable failure chain, the unsupported claim or broken
requirement, and the minimum correction. Put non-blocking release operations,
portability limitations, and evidence improvements in gaps/risks rather than
inflating them into implementation blockers.
