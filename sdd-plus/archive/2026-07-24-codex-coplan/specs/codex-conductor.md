# Capability (delta): codex-conductor

Capability: codex-conductor

Adds two-brain plan negotiation: the pilot drafts a plan and negotiates it with Codex as an equal peer before any code is written — a read-only critique round plus a bounded loop that guarantees termination.

## ADDED Requirements

### Requirement: Plan negotiation is a read-only peer critique
`negotiate.py` SHALL send an implementation plan to Codex as an equal peer and return a schema-locked critique — an honest overall take, a `converged` flag, `blocking_concerns`, `gaps`, `risks`, and a `decomposition` proposing per-task owner (claude/codex/either) and model tier (flagship/workhorse/cheap). It SHALL be read-only, SHALL frame the plan as data behind a boundary marker the content cannot close, and SHALL refuse to send a plan that is empty or appears to contain secret material — before Codex is spawned.

- **WHEN** a real plan is negotiated
- **THEN** Codex returns a structured critique routed to a fuel-appropriate model, and the critique is the pilot's input to audit — never authoritative

- **WHEN** the plan is empty or looks secret-bearing
- **THEN** the run is refused (`empty_plan` / `secret_content`) and no plan is sent

- **WHEN** the plan text contains the boundary marker
- **THEN** the marker escalates so the plan cannot close its own fence

### Requirement: The negotiation loop is bounded and terminates
A pure `loop_should_continue(critique, round, cap)` SHALL decide whether to negotiate another round, and SHALL stop when Codex has genuinely converged (the `converged` flag AND no blocking concerns) or the round cap is reached. The cap SHALL be the hard stop that prevents the two brains from consuming flagship tokens indefinitely. A `converged` flag that still lists blocking concerns SHALL NOT be trusted.

- **WHEN** Codex reports converged with no blocking concerns
- **THEN** the loop stops — both brains agree

- **WHEN** blocking concerns remain and the cap is not reached
- **THEN** the loop continues for another round

- **WHEN** the round cap is reached
- **THEN** the loop stops regardless of remaining concerns — the pilot decides

- **WHEN** Codex reports `converged: true` but still lists blocking concerns
- **THEN** the contradiction is not trusted and the loop does not treat it as converged
