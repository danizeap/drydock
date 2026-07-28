# SDD+ Skill Framework Dogfood Observation

## Session Identity

- Date: 2026-07-28
- Project: Drydock
- Repository: `C:\Users\Daniel Paez\drydock`
- Task: Finish schema-v2 adaptive delegation evidence and learn from the orchestration cost.
- Project type: framework
- Starting knowledge state: KNOWN_AND_MAPPED

## Routing

- Execution mode: FULL
- Recommended model: flagship for architecture/review; workhorse for bounded implementation and verification
- Model actually used: Codex flagship/workhorse plus Claude Opus 5 and Fable 5 peer attempts
- Recommended reasoning level: high for architecture and security boundaries
- Reasoning level actually used: high/xhigh
- Current-model action: continued with bounded fallback
- Primary skill: drydock-orchestrate
- Supporting skills: drydock-lifecycle, backend, testing
- Human approvals required: integration and push were Owner-authorized; release remains unauthorized

## Context Use

- Maps loaded: current packet, project protocol, branch/worktree state
- Source files loaded: delegation contracts, ledger, profiles, bundle builder, and focused tests
- Historical documents loaded: prior verifier and Opus blocker results
- Context explicitly excluded: unrelated application code and inactive packet implementation details
- Context expanded during task? yes
- Why context expanded: Opus review after implementation found schema-v2 and repair blockers that required a substantial redesign.

## Escalation

- Model escalated? yes
- Mode escalated? no; the task was FULL from entry
- Supporting skill added? yes
- New bounded task created? yes; isolated mutation and verifier worktrees
- Reason: security-sensitive persistent evidence contracts required independent execution and review boundaries

## Execution And Proof

- Files changed: 18 candidate files plus this packet's final review evidence
- Tests or verification run: focused suites, full adapter and legacy suites, parity checks, direct multi-interpreter smoke, independent Codex verifier, and Claude repository-aware review
- Report type: FULL unified
- Result: PASS WITH OPEN QUESTIONS for candidate code convergence; full release verification remains BLOCKED
- Unexpected changes or limitations: the Owner reported roughly 11 percent of weekly Codex capacity consumed; elapsed work was about an hour before final peer closure. Two automated Claude peer calls embedded a 297 KB review bundle and hit their $1 ceilings without verdicts.

## Framework Observation

- Useful framework intervention: immutable worktrees, exact commit binding, fail-closed verification, and cross-model review found real schema, repair, locking, and naming defects before integration.
- Unnecessary context or ceremony: broad context was repeatedly loaded by flagship workers; full suites were rerun after review-driven redesign; a duplicate verifier was briefly started; late architecture review caused expensive rework.
- Friction encountered: the tool-isolated peer cannot read a bounded repository snapshot, so large code review requires embedding source into the prompt. Both Opus 5 and Fable 5 exceeded the $1 controller ceiling without returning a verdict.
- What the framework prevented: prefix-only repair without visible in-chain history, overclaimed verification naming, weak contention proof, and noncanonical replay.
- What the framework failed to catch: `error_max_budget_usd` was classified as an ordinary process failure with `continue_codex_only`, despite the peer-unavailable spec requiring budget violations to return to the Owner.
- Owner confidence: medium
- Simplification recommendation: negotiate architecture before implementation; freeze the candidate before the only full-suite pass; allow one implementation worker and one verifier; give every phase elapsed-time and capacity budgets; use targeted tests until the diff freezes; transport a digest-bound read-only review snapshot instead of embedding the full implementation.
- Rule or skill that may need revision: `drydock-orchestrate` should define a review-input budget, reject oversized embedded reviews before provider spend, persist peer output durably, and route budget-ceiling failures to the Owner.

## Follow-Up

- Next bounded task: orchestration-efficiency-hardening
- Next recommended mode/model/skill: FULL architecture slice first, then STANDARD bounded backend/testing implementation
- Requires protocol change now? no
- Notes: preserve plan peer critique, independent verification, fail-closed checks, and final evidence. Reduce duplicated work and oversized context; do not waive safety gates.
