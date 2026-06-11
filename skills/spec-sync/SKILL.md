---
name: spec-sync
description: Merge a change packet's delta specs into the living capability specs. Use when archiving a change, when the user asks to sync specs, or when delta specs under sdd-plus/changes/<name>/specs/ have been implemented and the main specs must reflect them. Agent-driven intelligent merge - not a mechanical copy.
---

# Spec Sync Skill

Living capability specs at `sdd-plus/specs/capabilities/<capability>.md` are the durable source of truth for what the system does. Change packets carry *delta specs* (`sdd-plus/changes/<name>/specs/<capability>.md`) describing intent. This skill merges deltas into the living specs so documentation never drifts from shipped behavior.

## Procedure

1. Locate delta spec files under the change's `specs/` directory. If the change name is ambiguous, ask — never guess which change to sync.
2. For each capability delta, read **both** the delta and the living spec (`sdd-plus/specs/capabilities/<capability>.md`; it may not exist yet).
3. Apply changes intelligently:
   - **ADDED** — add the requirement; if it already exists, treat as implicit MODIFIED and update it to match.
   - **MODIFIED** — find the requirement and apply only the stated changes (new scenarios, changed scenarios, updated description). **Preserve every scenario and sentence the delta does not mention.**
   - **REMOVED** — delete the entire requirement block.
   - **RENAMED** — find the FROM heading, rename to TO, keep content.
4. If the living spec does not exist, create it with a Purpose section (brief, `TBD` acceptable) and a Requirements section holding the ADDED requirements.
5. Summarize per capability: requirements added / modified / removed / renamed.

## Rules

- The delta is intent, not replacement — partial updates are the norm.
- The operation must be idempotent: running twice produces the same living spec.
- Never invent requirements that are in neither the delta nor the living spec.
- If a MODIFIED/REMOVED/RENAMED target cannot be found in the living spec, stop and ask rather than guessing.
- Show what you change as you go; this edit is itself subject to normal review.
- Requirement style: "The system SHALL <behavior>" with `#### Scenario:` blocks using **WHEN/THEN** bullets. Keep new content in this style.

## Result

`PASS` with the per-capability summary, or `BLOCKED` naming the ambiguity that prevented a safe merge.
