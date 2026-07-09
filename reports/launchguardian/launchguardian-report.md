# LaunchGuardian Report

## Launch Decision

**INCOMPLETE**

LaunchGuardian could not produce a complete approval because required validation or scanner coverage is incomplete.

## Executive Summary

- Target: `C:\Users\Daniel Paez\drydock`
- Mode: `framework`
- Validation mode: `framework`
- Scan mode: `local`
- Generated at: `2026-07-09T13:27:18.289177Z`
- LGF validation status: **valid**
- Strict scanners: **false**
- Total findings: **0**
- Scanner findings: **0**
- Blocking findings: **0**
- Severity counts: **critical**: 0, **high**: 0, **medium**: 0, **low**: 0, **info**: 0

## Scanner Summary

| Scanner | Status | Findings | Blocking Findings |
| --- | --- | ---: | ---: |
| api_surface | ran | 0 | 0 |
| frontend_exposure | ran | 0 | 0 |
| gitleaks | ran | 0 | 0 |
| semgrep | failed | 0 | 0 |
| trivy | ran | 0 | 0 |

## Top Blockers

No open blocking findings.

## Recommended Next Actions

1. Restore scanner coverage for: `semgrep`.
2. Complete missing scanner or LGF coverage before treating this as approved.
3. Re-run `launchguardian scan --target .` after remediation and attach the updated report.

## Findings By Severity

No findings.

## Findings By Gate

No findings.

## Configuration

- Config file found: **false**
- Config file: `not found`
- Configured output dir: `reports\launchguardian`
- Effective output dir: `C:\Users\Daniel Paez\drydock\reports\launchguardian`
- Disabled scanners: `none`
- Active exclusions: `paths=node_modules, .git, reports/launchguardian; globs=**/*.min.js, **/fixtures/**`
- Severity policy: `critical_blocks: true`, `high_blocks: true`, `medium_blocks: false`, `low_blocks: false`
- Config warnings/blockers: **0**

## All Findings

No findings.
