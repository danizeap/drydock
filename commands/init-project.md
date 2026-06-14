---
description: Scaffold Drydock (SDD+) into the current repository
---
Initialize Drydock in this project. Scaffold source: `${CLAUDE_PLUGIN_ROOT}/assets/project-scaffold/`.

1. **Never overwrite.** For every file/folder below, copy it only if it does not already exist; if it exists, leave it untouched and report "kept existing".
2. Copy into the project root: `AGENTS.md`, `CLAUDE.md`, `PROJECT_CONTEXT.template.md`, `scripts/sdd.py`, `scripts/sdd.ps1`, the full `sdd-plus/` tree, and merge `.gitignore` entries (append missing lines only).
3. If the project already has a `CLAUDE.md` or `AGENTS.md`, do not replace it — instead show the Owner the Drydock version and offer to merge the relevant sections.
4. Run `python3 scripts/sdd.py init` (on Windows: `python`) to ensure the directory structure. Requires Python 3.9+.
5. **Brownfield repos:** offer to run the `codebase-cartographer` skill to produce initial repo maps, and `/drydock:init-standards` to generate stack-specific standards.
6. **Greenfield repos:** start the first-run context interview and create `PROJECT_CONTEXT.md` from the template.
7. **Scanner check.** Detect whether the LaunchGuardian scanner is installed (`launchguardian --version`). If missing, tell the Owner: "Drydock's security gates use an optional local scanner. Install it with `pip install launchguardian` — everything else works without it, but release reviews will report INCOMPLETE until it's present." Offer to run the install now if the Owner wants.
8. Report exactly what was created, what was kept, whether the scanner is available, and the recommended next step (`/drydock:onboard` for first-time users).

Portability note: if the Owner also uses non-Claude agents (e.g. Codex) in this repo, offer to additionally copy the plugin's `skills/` into the project's `.claude/skills/` so the full skill definitions live in project files all agents can read. Mention the tradeoff: project copies do not auto-update with the plugin.
