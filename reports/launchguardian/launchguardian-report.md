# LaunchGuardian Report

## Launch Decision

**APPROVED_WITH_DISPOSITIONS**

No open blocking findings remain, and **6** finding(s) use exact reviewed dispositions. The recorded approver metadata is auditable project evidence, not authenticated proof of human identity.

## Executive Summary

- Target: `C:\Users\Daniel Paez\drydock`
- Mode: `framework`
- Validation mode: `framework`
- Scan mode: `local`
- Generated at: `2026-07-25T15:16:29.577002Z`
- LGF validation status: **valid**
- Strict scanners: **true**
- Total findings: **6**
- Scanner findings: **6**
- Blocking findings: **0**
- Severity counts: **critical**: 0, **high**: 6, **medium**: 0, **low**: 0, **info**: 0
- Finding status counts: **not_applicable**: 6

## Scanner Summary

| Scanner | Status | Findings | Blocking Findings |
| --- | --- | ---: | ---: |
| api_surface | ran | 0 | 0 |
| frontend_exposure | ran | 0 | 0 |
| gitleaks | ran | 0 | 0 |
| semgrep | ran | 6 | 0 |
| trivy | ran | 0 | 0 |

## Top Blockers

No open blocking findings.

## Recommended Next Actions

1. Reconfirm each reviewed finding disposition when its rule, evidence, supported-runtime boundary, or launch scope changes.
2. Re-run `launchguardian scan --target .` after remediation and attach the updated report.

## Findings By Severity

### High (6)

| Severity | Blocks | Status | Source | Gate | Location | Finding | Why It Matters | Review Or Fix |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |


## Findings By Gate

### Gate 3 — Code Security (6)

| Severity | Blocks | Status | Source | Location | Finding | Why It Matters | Review Or Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high | yes | not_applicable | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |


## Configuration

- Config file found: **true**
- Config file: `C:\Users\Daniel Paez\drydock\launchguardian.yml`
- Configured output dir: `reports\launchguardian`
- Effective output dir: `C:\Users\Daniel Paez\drydock\reports\launchguardian`
- Disabled scanners: `none`
- Active exclusions: `paths=node_modules, .git, reports/launchguardian; globs=**/*.min.js, **/fixtures/**`
- Severity policy: `critical_blocks: true`, `high_blocks: true`, `medium_blocks: false`, `low_blocks: false`
- Config warnings/blockers: **0**
- Reviewed finding dispositions configured: **2**
- Findings with applied dispositions: **6**

## Reviewed Finding Dispositions

| Source | Rule ID | Status | Approved | Reason | Evidence | Applied Findings |
| --- | --- | --- | --- | --- | --- | --- |
| semgrep | python.lang.compatibility.python36.python36-compatibility-Popen1 | not_applicable | 2026-07-25 by Daniel Paez | The rule checks compatibility with Python versions below Drydock's supported runtime floor. | AGENTS.md, PROJECT_CONTEXT.md, and README.md require Python 3.9+; .github/workflows/ci.yml tests Python 3.9 and 3.12; Codex readiness rejects runtimes below 3.9. | 3 |
| semgrep | python.lang.compatibility.python36.python36-compatibility-Popen2 | not_applicable | 2026-07-25 by Daniel Paez | The rule checks compatibility with Python versions below Drydock's supported runtime floor. | AGENTS.md, PROJECT_CONTEXT.md, and README.md require Python 3.9+; .github/workflows/ci.yml tests Python 3.9 and 3.12; Codex readiness rejects runtimes below 3.9. | 3 |

## All Findings

| Severity | Blocks | Status | Source | Gate | Location | Finding | Why It Matters | Review Or Fix |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | not_applicable | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
