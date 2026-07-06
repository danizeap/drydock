---
description: Verify an SDD+ change - artifacts, tasks, spec coverage, and claims
---
Verify the SDD+ change: $ARGUMENTS (if ambiguous, list changes via `python3 scripts/sdd.py status` — on Windows `python` — and ask).

Script resolution: use `./scripts/sdd.py` if it exists in the project, otherwise `"${CLAUDE_PLUGIN_ROOT}/scripts/sdd.py"`; if neither resolves, tell the Owner to run /drydock:init-project first.

1. Run `python3 scripts/sdd.py verify <name>` and report its output (missing artifacts, TBD placeholders, pending tasks).
2. If the change has delta specs, check **spec coverage**: for each requirement, search the codebase for implementation evidence and each scenario for test evidence. Report per requirement: IMPLEMENTED (file:line) / NOT FOUND / PARTIAL.
3. Invoke the `verifier` subagent for independent review of the diff, tests, and evidence claims.
4. Output a unified result: COMPLETENESS (tasks, artifacts), CORRECTNESS (requirement→implementation mapping, tests), COHERENCE (follows existing patterns and the plan). Verdict: PASS / PASS WITH OPEN QUESTIONS / BLOCKED.
