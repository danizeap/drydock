---
description: Show active SDD+ changes and their state
---
Script resolution rule for all steps: use `./scripts/sdd.py` if it exists in the project; otherwise use `"${CLAUDE_PLUGIN_ROOT}/scripts/sdd.py"`. If neither resolves, tell the Owner to run /drydock:init-project first.

Run `python3 scripts/sdd.py status` (on Windows: `python`) and present the result. For each active change, note whether it has delta specs (a `specs/` directory with content) and whether they appear synced into `sdd-plus/specs/capabilities/`. Flag anything stalled or BLOCKED from earlier sessions.

This is the engineering view. If the Owner is asking in product terms ("how's my project?", "is it safe to promise?"), offer `/drydock:brief` instead of pasting this output.
