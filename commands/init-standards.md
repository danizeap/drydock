---
description: Generate stack-specific engineering standards for this project
---
Generate project-specific standards for this repository.

1. Determine the actual stack: inspect manifests (package.json, pyproject.toml, etc.) and ask the Owner for anything undetectable — backend stack, database/ORM, API style, frontend stack, testing stack, CI/tooling.
2. Write `sdd-plus/standards/stack-standards.md`: concrete conventions for THIS stack — project structure, naming, typing, error handling, validation, testing patterns, lint/format commands. Be specific and deterministic ("services live in `src/services/`, validated with zod schemas in `src/schemas/`"), not generic advice.
3. Do not duplicate the generic standards (`engineering-standards.md`, `security-shipping-standards.md`); this file is the stack-specific layer on top of them.
4. Keep it under ~150 lines. Standards nobody reads are theater.
