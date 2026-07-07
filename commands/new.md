---
description: Start a new SDD+ change packet, with optional delta specs
---
Create a new SDD+ change for: $ARGUMENTS

Script resolution: use `./scripts/sdd.py` if it exists in the project, otherwise `"${CLAUDE_PLUGIN_ROOT}/scripts/sdd.py"`; if neither resolves, tell the Owner to run /drydock:init-project first. Invoke it with `python3` (on Windows: `python`).

1. If no kebab-case change name can be derived from the arguments, propose one and confirm.
2. Run `python3 scripts/sdd.py new <name>` (on Windows: `python`).
3. Fill `brief.md` and `plan.md` from the conversation context — never leave TBD placeholders if the information exists. Run task intake per `sdd-plus/protocols/framework-usage.md` (mode, primary skill, approvals).
   Include a `## What this means for your product` section in brief.md: ONE sentence in the Owner's own language, future-neutral, naming who notices and what they can then do or stop worrying about ("After X, you can Y"). No marketing virtues ("more robust!") — the Owner brief renders this line verbatim as the item's face, prefixed as a goal until the work is done.
4. If the change modifies system behavior, create delta spec(s) in the change's `specs/` directory using `sdd-plus/templates/spec-delta.md` — testable SHALL requirements with WHEN/THEN scenarios for each affected capability.
5. State the selected execution mode, primary skill, and stop conditions before implementing anything.
