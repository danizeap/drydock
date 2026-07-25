---
name: drydock-lifecycle
description: Operate the Drydock SDD+ change lifecycle in an initialized repository. Use for Drydock status, new change packets, verification, spec sync, or archive requests.
---

# Operate the SDD+ lifecycle

This Codex skill follows the repository's agent-neutral procedure. It does not
promise Claude slash-command behavior.

1. Read `AGENTS.md`, `PROJECT_CONTEXT.md`,
   `sdd-plus/protocols/framework-usage.md`, and only the standards and operating
   skill needed for the requested work.
2. If project context is missing or template-like, stop before meaningful
   implementation and ask the Owner for the required facts.
3. Use the repository's `scripts/sdd.py` with the current Python interpreter:
   `status`, `new <kebab-name>`, `verify <kebab-name>`, or
   `archive <kebab-name>` as appropriate.
4. Write testable delta specifications before implementing behavior changes.
   Keep `tasks.md`, `decision-log.md`, and `verification.md` current.
5. Treat the implementing agent's report as evidence, not independent
   verification. Do not archive until verification, spec sync, API/document
   gates, and required human approvals are satisfied.
6. Never turn a missing check, timeout, or unknown state into PASS.

For spec sync, follow the repository's `spec-sync` operating skill and merge
the change packet's delta into living capability specs before archive.
