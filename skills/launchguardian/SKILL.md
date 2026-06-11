---
name: launchguardian
description: Secure-shipping review — is this project safe enough to ship? Use for release, deployment, or security review of a local owned repo, validating LaunchGuardian Framework files, and running defensive scanner checks via launchguardian-cli. Graduated skill - the procedure lives in the launchguardian-cli tool. Never for unauthorized scanning, third-party targets, or offensive work.
---

# LaunchGuardian Skill (graduated)

This skill graduated into the `launchguardian-cli` tool. It remains registered so the agent knows when to invoke the tool and what boundaries apply. It is a *defensive, local-only, permission-bound* shipping reviewer — not a hacking agent. Use it for meaningful release/deployment/security decisions, not every commit. Implementation work belongs to the implementation skills.

## Boundaries (absolute)

Local-only. Owned repos only. No unauthorized scanning, no third-party targets, no offensive exploitation, no credential abuse, no active web scanning. Never claim a repo is safe without evidence. Never replace human review for high-risk launches.

## Availability check

Before running commands, check the scanner is installed (`launchguardian --version`). If missing, tell the Owner: install with `pip install launchguardian` (PyPI). Scans without it report INCOMPLETE with scanner_unavailable findings — never present such a run as a completed security review.

## Commands

```bash
launchguardian validate-lgf --target .            # LGF file validation
launchguardian scan --target .                    # full local scan
launchguardian scan --target . --framework-mode   # for framework/template/tool repos
launchguardian scan --target . --strict-scanners  # release-quality CI gate
```

Scanner stack: Gitleaks (secrets, Gate 4), Semgrep (static security, Gates 3/7/8), Trivy (deps/IaC, Gates 10/11/4), native frontend-exposure (Gates 5/4/8) and API-surface (Gates 6/7/8/19) scanners.

## Procedure

1. Confirm the target is local, owned, and permission-bound.
2. Validate LGF files first; run scanners against the local target.
3. Summarize findings in practical shipping language; mark each blocking / follow-up / informational.
4. Result: `PASS` (no launch-blocking findings, required checks completed), `PASS WITH FOLLOW-UP` (no blocker, tracked risks remain), or `FAIL` (a blocking risk exists, validation failed, or evidence is insufficient to support shipping).

Framework rules (gates, severity, skip confirmation) live in `sdd-plus/specs/launchguardian-framework.md` and `sdd-plus/standards/security-shipping-standards.md`. Critical findings block launch until fixed and verified, removed from scope, or downgraded by new evidence. Humans must confirm skipped high-risk gates.

## Evidence

Target reviewed, framework files inspected, commands run, findings by severity/launch impact, result, assumptions and follow-ups.
