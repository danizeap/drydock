# LaunchGuardian Report

## Launch Decision

**BLOCKED**

Launch is blocked by **6** open blocking finding(s). Fix the issue, remove the affected feature from scope, or document an approved exceptional override before launch.

## Executive Summary

- Target: `C:\Users\Daniel Paez\drydock`
- Mode: `framework`
- Validation mode: `framework`
- Scan mode: `local`
- Generated at: `2026-07-25T14:03:54.497175Z`
- LGF validation status: **valid**
- Strict scanners: **true**
- Total findings: **6**
- Scanner findings: **6**
- Blocking findings: **6**
- Severity counts: **critical**: 0, **high**: 6, **medium**: 0, **low**: 0, **info**: 0

## Scanner Summary

| Scanner | Status | Findings | Blocking Findings |
| --- | --- | ---: | ---: |
| api_surface | ran | 0 | 0 |
| frontend_exposure | ran | 0 | 0 |
| gitleaks | ran | 0 | 0 |
| semgrep | ran | 6 | 6 |
| trivy | ran | 0 | 0 |

## Top Blockers

| Severity | Blocks | Source | Gate | Location | Finding | Why It Matters | Review Or Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |

## Recommended Next Actions

1. Resolve or explicitly remove from launch scope the **6** open blocking finding(s).
2. Re-run `launchguardian scan --target .` after remediation and attach the updated report.

## Findings By Severity

### High (6)

| Severity | Blocks | Source | Gate | Location | Finding | Why It Matters | Review Or Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |


## Findings By Gate

### Gate 3 — Code Security (6)

| Severity | Blocks | Source | Location | Finding | Why It Matters | Review Or Fix |
| --- | --- | --- | --- | --- | --- | --- |
| high | yes | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |


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

| Severity | Blocks | Source | Gate | Location | Finding | Why It Matters | Review Or Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\orchestrator.py:389 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\adapters\codex\drydock\scripts\process_runner.py:805 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen1 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
| high | yes | semgrep | Gate 3 — Code Security | C:\Users\Daniel Paez\drydock\scripts\conductor\codex_bridge.py:91 | Semgrep finding: python.lang.compatibility.python36.python36-compatibility-Popen2 | Static analysis identified code that may introduce a security weakness. | Review the Semgrep finding, confirm exploitability, and remediate or document an accepted risk. |
