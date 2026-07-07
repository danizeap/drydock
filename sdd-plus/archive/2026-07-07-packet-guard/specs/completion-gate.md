# Spec Delta: packet-guard

Capability: completion-gate

One addition surfaced by this change's red-team: the completion gate's nudge persistence rebuilt the shared state dict from its own known fields, silently dropping keys other hooks own (the packet guard's `warned` flag). This delta adds the shared-state writer contract as a spec-level requirement.

## ADDED Requirements

### Requirement: Shared-state writers preserve foreign keys
Every writer of the per-session state file (orientation stamp, completion gate, packet guard, and any future hook) SHALL copy-and-update the existing state dict, preserving keys it does not own — never reconstructing the dict from its own fields. Validation SHALL remain permissive toward unknown keys so hooks of different versions interoperate.

#### Scenario: Nudge persistence preserves the warned flag
- **WHEN** the packet guard has set `warned` and the completion gate later persists a nudge in the same session
- **THEN** the rewritten state still carries `warned` (and any other foreign keys)
