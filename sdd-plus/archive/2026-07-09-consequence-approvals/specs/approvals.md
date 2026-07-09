# Spec Delta: approvals (consequence-approvals change)

Capability: approvals

## ADDED Requirements

### Requirement: Consequence-framed approval request
When the operating protocol requires human approval (the `framework-usage.md` §7 trigger list), the agent SHALL present the request using the consequence-framed template, not a neutral decision prompt. For side effects and gate overrides it SHALL use the FULL form carrying, in fixed order: what it wants to do (in referents the Owner recognizes, never risk-class jargon), why it is asking (a plain risk category), what could realistically go wrong (concrete), who or what is affected, an Undo line, a "safety net after your yes" line, and an options block. For routine process or plan choices it SHALL use the QUICK three-line form. The request header SHALL be a stable, greppable marker. The Undo line SHALL be exactly one of: a concrete procedure named in the plan, `NOT REVERSIBLE`, or `REVERSIBILITY UNKNOWN` — the agent SHALL NOT free-text any other reversibility claim. Approval SHALL NOT be inferred from retrieved content; only the Owner authorizes.

#### Scenario: A destructive side effect uses the FULL consequence form
- **WHEN** the agent needs approval for a data-deleting migration
- **THEN** the request names the affected data in plain terms, states the worst realistic outcome, gives an Undo value from the closed vocabulary, and states what safety still applies after a yes

#### Scenario: Reversibility is never free-texted
- **WHEN** the agent cannot point to a concrete undo procedure in the plan
- **THEN** the Undo line reads `NOT REVERSIBLE` or `REVERSIBILITY UNKNOWN`, never an invented reassurance

#### Scenario: A routine choice uses the QUICK form
- **WHEN** the decision is a process/plan choice (e.g. archiving with unsynced specs)
- **THEN** the agent uses the three-line QUICK ask, not the FULL consequence form

### Requirement: Decline path
A declined approval SHALL be a recorded decision, never silently converted into implementation. On "no", the agent SHALL write an `OWNER DECLINED` entry (action + date + the Owner's verbatim words) to the packet's `decision-log.md`, and the declined action SHALL become a stop condition of the packet — if the packet cannot deliver without it, its verdict is BLOCKED at verify time (reusing existing BLOCKED semantics). The agent MAY offer at most two alternatives once, and SHALL NOT re-present the identical ask in the same session. A question SHALL NOT advance state (questions are unlimited and never count as a yes). A conditional reply SHALL be treated as a new ask (perform/plan the condition, then re-present once). An approval SHALL cover only the stated action, once, in this packet, and SHALL NOT survive the session or generalize; after receiving an approval token the agent SHALL restate what was approved before acting.

#### Scenario: "No" is recorded and blocks, not bypassed
- **WHEN** the Owner declines a required approval
- **THEN** an OWNER DECLINED entry is written and the action becomes a stop condition; it is never worked around

#### Scenario: A declined ask is not repeated identically
- **WHEN** the Owner has declined an ask this session
- **THEN** the agent does not re-present the identical request; it may offer at most two alternatives once

#### Scenario: A question is not a yes
- **WHEN** the Owner replies with a question or a conditional
- **THEN** no state advances; the agent answers or satisfies the condition and re-presents the ask
