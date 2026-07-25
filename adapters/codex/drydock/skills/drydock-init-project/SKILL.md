---
name: drydock-init-project
description: Initialize Drydock's agent-neutral SDD+ project scaffold in a repository. Use when the Owner asks to initialize, onboard, or add Drydock governance to a repository.
---

# Initialize a Drydock project

This is a Codex skill, not a Claude slash-command alias.

1. Resolve this plugin's root from the loaded skill and locate
   `scripts/drydock_codex.py`.
2. Run `python <plugin-root>/scripts/drydock_codex.py init --root <repository>`
   without `--apply`. Treat its JSON as a preview, not proof that anything was
   written.
3. Show the Owner the files that would be created, existing conflicts, and
   `.gitignore` lines that would be added. Stop on any reported error.
4. Only an explicit request to initialize or an explicit approval of that
   preview authorizes `--apply`.
5. Run the same command with `--apply`. Existing non-`.gitignore` files are
   never overwritten. The initializer never installs `.git/hooks/pre-commit`.
6. Ask the Owner for project context when `PROJECT_CONTEXT.md` is absent or
   template-like. Never invent those answers.
7. Run the readiness skill and report its evidence. Do not describe hooks,
   peer review, or enforcement as active unless readiness proves them for the
   current task.

The generated scaffold is verified by digest before any write. Failure,
conflict, and unknown states remain explicit; they are never converted to a
positive result.
